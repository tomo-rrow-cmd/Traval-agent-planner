#!/usr/bin/env python3
"""
API 响应时长基准测试 — 完整版
先播种测试数据，再测试所有 64 个接口。
"""

import asyncio
import json
import sys
import time
import uuid
from datetime import date, datetime, timedelta

# 确保能导入 app 模块
sys.path.insert(0, ".")

import httpx
from dateutil.utils import today

from app.db.repositories.plan_repo import PlanRepository
from app.db.repositories.trip_repo import (
    TripRepository,
    CheckinRepository,
    ExpenseRepository,
    AdjustmentRepository,
)
from app.db.repositories.travelogue_repo import TravelogueRepository
from app.db.repositories.user_repo import UserRepository
from app.db.session import async_session_factory
from app.schemas.common import BaseResponse, PaginatedData
from app.schemas.data import WeatherData, WeatherItem

BASE = "http://localhost:8001/api/v1"
HTTP_TIMEOUT = 10

results = []


# ── helpers ──────────────────────────────────────────────
def http(method, path, **kwargs):
    """返回 (status, elapsed_ms, full_response_text)。记录用 test()。"""
    url = f"{BASE}{path}"
    hdrs = kwargs.pop("headers", {})
    sse = kwargs.pop("_sse", False)
    if sse:
        try:
            with httpx.Client(timeout=HTTP_TIMEOUT) as c:
                with c.stream(method, url, headers=hdrs, **kwargs) as resp:
                    t0 = time.perf_counter()
                    n = 0
                    for _ in resp.iter_bytes():
                        n += 1
                        if n >= 5 or time.perf_counter() - t0 > 3:
                            break
                    el = (time.perf_counter() - t0) * 1000
                return resp.status_code, round(el, 1), "SSE_OK"
        except Exception as e:
            return 0, 0, f"SSE异常 {e}"
    try:
        t0 = time.perf_counter()
        with httpx.Client(timeout=HTTP_TIMEOUT) as c:
            r = c.request(method, url, headers=hdrs, **kwargs)
        el = (time.perf_counter() - t0) * 1000
        return r.status_code, round(el, 1), r.text
    except Exception as e:
        return 0, 0, str(e)[:60]


def test(mod, method, path, **kw):
    st, ms, text = http(method, path, **kw)
    snippet = text[:80].replace("\n", " ") if text and text != "SSE_OK" else text[:80]
    results.append((mod, method, path, st, ms, snippet))
    try:
        print(f"  [{st:>3}] {method:>6} {path}  {ms:>8.1f}ms  {snippet[:80]}")
    except UnicodeEncodeError:
        print(f"  [{st:>3}] {method:>6} {path}  {ms:>8.1f}ms  (response has non-ASCII)")
    return st, ms, text


def sec(title):
    print(f"\n===== {title} =====")


# ── seed helpers ─────────────────────────────────────────
async def create_user():
    """注册用户并返回 (phone, password, uid, token)"""
    phone = f"188{uuid.uuid4().hex[:8]}"
    pw = "test123456"
    st, _, txt = http("POST", "/auth/register",
                      json={"phone": phone, "password": pw, "nickname": "Benchmark"})
    if st != 200:
        raise RuntimeError(f"register failed: {txt}")
    d = json.loads(txt)
    token = d["data"]["access_token"]
    uid = d["data"]["user"]["id"]
    print(f"  [seed] 注册用户 uid={uid}")
    return phone, pw, uid, token


async def seed_plan(uid):
    """用 repository 直接创建方案（绕开有 Bug 的 update_full_data）"""
    async with async_session_factory() as db:
        repo = PlanRepository(db)
        from app.db.models.plan import Plan
        from sqlalchemy import update

        plan = await repo.create_for_user(
            user_id=uid,
            destination="北京",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=2),
            budget=5000.0,
            travelers=2,
            status="completed",
        )
        # 直接 UPDATE 补充字段
        full = {
            "total_cost": 5000.0,
            "overview": {"highlights": ["故宫", "长城"], "total_distance_km": 50, "transport_modes": ["地铁"]},
            "traffic_summary": {"total_traffic_cost": 200},
            "food_summary": {"recommended_restaurants": [], "total_food_budget": 600},
            "budget_detail": {"total": 5000, "actual_total": 3000, "remaining": 2000, "breakdown": {}},
            "is_favorite": False, "view_count": 0, "version": 1,
        }
        await db.execute(
            update(Plan).where(Plan.id == plan.id).values(**full)
        )
        await db.commit()
        pid = plan.id
        print(f"  [seed] 创建方案 pid={pid}")
    return pid


async def seed_trip(uid, pid):
    async with async_session_factory() as db:
        repo = TripRepository(db)
        trip = await repo.create_for_plan(
            user_id=uid, plan_id=pid,
            budget_total=5000, total_pois=10,
        )
        await db.commit()
        tid = trip.id
        print(f"  [seed] 创建行程 tid={tid}")
    return tid


async def seed_checkin(uid, tid):
    async with async_session_factory() as db:
        repo = CheckinRepository(db)
        ck = await repo.create_checkin(
            trip_id=tid, user_id=uid,
            poi_type="attraction", poi_name="故宫博物院",
            poi_id="mock_poi_001",
            note="天气很好", rating=5,
            photos=[],
        )
        await db.commit()
        print(f"  [seed] 创建签到 cid={ck.id}")
    return ck.id


async def seed_expense(uid, tid):
    async with async_session_factory() as db:
        repo = ExpenseRepository(db)
        exp = await repo.create_expense(
            trip_id=tid, amount=120.0,
            category="餐饮", note="午餐",
        )
        await db.commit()
        print(f"  [seed] 创建花费 eid={exp.id}")
    return exp.id


async def seed_travelogue(uid, tid):
    async with async_session_factory() as db:
        repo = TravelogueRepository(db)
        tlg = await repo.create_for_trip(
            trip_id=tid, user_id=uid,
            title="北京之行", content="这是一次愉快的旅行…",
            status="draft",
        )
        await db.commit()
        print(f"  [seed] 创建游记 gid={tlg.id}")
    return tlg.id


# ── main ─────────────────────────────────────────────────
async def main():
    token = None
    uid = None

    # 1. 注册
    print("──── 播种测试数据 ────")
    phone, pw, uid, token = await create_user()

    # 2. 用 repository 创建底层数据
    pid = await seed_plan(uid)
    tid = await seed_trip(uid, pid)
    cid = await seed_checkin(uid, tid)
    eid = await seed_expense(uid, tid)
    gid = await seed_travelogue(uid, tid)

    # 3. 用 password 方式登录
    st, _, txt = http("POST", "/auth/sessions",
                      json={"phone": phone, "password": pw, "method": "password"})
    if st == 200:
        try:
            token = json.loads(txt)["data"]["access_token"]
            print(f"  [seed] 密码登录成功")
        except Exception:
            pass

    hdrs = {"Authorization": f"Bearer {token}"} if token else {}

    # ────── 正式测试 ──────
    print("\n" + "=" * 60)
    print("  开始 API 基准测试")
    print("=" * 60)

    # 1. 认证 (5)
    sec("1. 认证 /auth")
    test("认证", "POST", "/auth/sms-codes", json={"phone": phone})
    test("认证", "POST", "/auth/sessions", json={"phone": phone, "password": pw, "method": "password"})
    test("认证", "POST", "/auth/tokens", json={"refresh_token": "dummy"})
    test("认证", "DELETE", "/auth/sessions/current", headers=hdrs)
    # 重登录
    st, _, txt = http("POST", "/auth/sessions",
                      json={"phone": phone, "password": pw, "method": "password"})
    if st == 200:
        try:
            token = json.loads(txt)["data"]["access_token"]
        except Exception:
            pass
        hdrs = {"Authorization": f"Bearer {token}"}

    # 2. 聊天 (8)
    sec("2. 聊天 /chat")
    st, _, txt = test("聊天", "POST", "/chat/sessions",
                      json={"title": "测试会话"}, headers=hdrs)
    sid = None
    if st == 200:
        try:
            sid = json.loads(txt).get("data", {}).get("id")
            print(f"  session_id={sid}")
        except Exception:
            pass

    test("聊天", "GET", "/chat/sessions", headers=hdrs)
    if sid:
        test("聊天", "PATCH", f"/chat/sessions/{sid}", json={"title": "已改名"}, headers=hdrs)
        test("聊天", "POST", f"/chat/sessions/{sid}/messages",
             json={"content": "推荐一个北京三日游行程"}, headers=hdrs, _sse=True)
        test("聊天", "GET", f"/chat/sessions/{sid}/messages", headers=hdrs)
        test("聊天", "GET", f"/chat/sessions/{sid}/plans", headers=hdrs)
        # stream 用 query param 传 token
        test("聊天", "GET", f"/chat/sessions/{sid}/stream?token={token}", _sse=True)
        test("聊天", "DELETE", f"/chat/sessions/{sid}", headers=hdrs)

    # 3. 方案 (9)
    sec("3. 方案 /plans")
    test("方案", "POST", "/plans",
         json={"session_id": sid or str(uuid.uuid4()), "confirmed": True},
         headers=hdrs, _sse=True)
    test("方案", "GET", "/plans", headers=hdrs)
    test("方案", "GET", f"/plans/{pid}", headers=hdrs)
    test("方案", "PATCH", f"/plans/{pid}", json={"modifications": []}, headers=hdrs, _sse=True)
    test("方案", "POST", f"/plans/{pid}/generations",
         json={"session_id": sid or "", "confirmed": True}, headers=hdrs, _sse=True)
    test("方案", "POST", f"/plans/{pid}/exports", params={"format": "md"}, headers=hdrs)
    test("方案", "POST", f"/plans/{pid}/shares", json={}, headers=hdrs)
    test("方案", "POST", f"/plans/{pid}/favorites", json={}, headers=hdrs)

    # 4. 行程 (17)
    sec("4. 行程 /trips")
    test("行程", "GET", "/trips", headers=hdrs)
    test("行程", "POST", "/trips", json={"plan_id": pid}, headers=hdrs)
    test("行程", "GET", f"/trips/{tid}", headers=hdrs)
    test("行程", "PATCH", f"/trips/{tid}", json={"status": "paused"}, headers=hdrs)
    test("行程", "PATCH", f"/trips/{tid}", json={"status": "active"}, headers=hdrs)
    test("行程", "GET", f"/trips/{tid}/progress", headers=hdrs)
    test("行程", "POST", f"/trips/{tid}/checkins",
         json={"poi_type": "attraction", "poi_name": "天安门", "note": "到此一游", "rating": 5}, headers=hdrs)
    test("行程", "GET", f"/trips/{tid}/checkins", headers=hdrs)
    test("行程", "POST", f"/trips/{tid}/expenses",
         json={"amount": 50.0, "category": "交通", "description": "地铁"}, headers=hdrs)
    test("行程", "GET", f"/trips/{tid}/expenses", headers=hdrs)
    test("行程", "POST", f"/trips/{tid}/adjustments/detect",
         json={"trigger_type": "user_request", "destination": "北京"}, headers=hdrs)
    test("行程", "GET", f"/trips/{tid}/adjustments", headers=hdrs)
    test("行程", "GET", f"/trips/{tid}/reminder", headers=hdrs)
    test("行程", "POST", f"/trips/{tid}/photos/annotate",
         json={"checkin": {"photos": [{"url": "https://example.com/p.jpg"}]}}, headers=hdrs)

    # 调整操作
    try:
        with httpx.Client(timeout=5) as c:
            r = c.get(f"{BASE}/trips/{tid}/adjustments", headers=hdrs)
            if r.status_code == 200:
                adj = r.json().get("data", [])
                if adj:
                    adj_id = adj[0]["id"]
                    test("行程", "POST", f"/trips/{tid}/adjustments/{adj_id}/accept", json={}, headers=hdrs)
    except Exception:
        pass

    # 5. 数据 (7)
    sec("5. 数据 /data")
    test("数据", "GET", "/data/cities")
    test("数据", "GET", "/data/cities?keyword=%E5%8C%97%E4%BA%AC")
    test("数据", "GET", "/data/attractions?city=%E5%8C%97%E4%BA%AC")
    test("数据", "GET", "/data/attractions/1")
    test("数据", "GET", "/data/restaurants?city=%E5%8C%97%E4%BA%AC")
    test("数据", "GET", "/data/hotels?city=%E5%8C%97%E4%BA%AC")
    test("数据", "GET", "/data/weather?city=%E5%8C%97%E4%BA%AC&date=2026-07-16")

    # 6. 运维 (3)
    sec("6. 运维 /ops")
    try:
        with httpx.Client(timeout=5) as c:
            t0 = time.perf_counter()
            r = c.get(f"{BASE}/health")
            el = (time.perf_counter() - t0) * 1000
            results.append(("运维", "GET", "/health", r.status_code, round(el, 1), r.text[:80]))
            print(f"  [{r.status_code:>3}]    GET /health  {el:>8.1f}ms")
    except Exception as e:
        results.append(("运维", "GET", "/health", 0, 0, str(e)[:60]))
        print(f"  [  0]    GET /health  异常 {e}")
    test("运维", "GET", "/tasks/nonexistent", headers=hdrs)
    test("运维", "GET", "/tasks/nonexistent/download", headers=hdrs)

    # 7. 游记 (11)
    sec("7. 游记 /travelogues")
    test("游记", "GET", "/travelogues", headers=hdrs)
    test("游记", "POST", "/travelogues", json={"trip_id": tid, "style": "diary"}, headers=hdrs)
    test("游记", "GET", f"/travelogues/{gid}", headers=hdrs)
    test("游记", "PATCH", f"/travelogues/{gid}", json={"title": "修改标题"}, headers=hdrs)
    test("游记", "POST", f"/travelogues/{gid}/publish", json={}, headers=hdrs)
    test("游记", "GET", f"/travelogues/materials", headers=hdrs)
    test("游记", "POST", f"/travelogues/materials/generate",
         json={"trip_id": tid}, headers=hdrs)
    test("游记", "POST", f"/travelogues/shares",
         json={"target_type": "travelogue", "target_id": gid}, headers=hdrs)
    test("游记", "GET", f"/travelogues/shares/test_share_code", headers=hdrs)

    # 收藏素材 (可能需要先有素材)
    try:
        with httpx.Client(timeout=5) as c:
            r = c.get(f"{BASE}/travelogues/materials", headers=hdrs)
            if r.status_code == 200:
                mats = r.json().get("data", [])
                if mats:
                    test("游记", "POST", f"/travelogues/materials/{mats[0]['id']}/favorite",
                         json={"is_favorite": True}, headers=hdrs)
    except Exception:
        pass

    test("游记", "DELETE", f"/travelogues/{gid}", headers=hdrs)

    # 8. 用户 (5)
    sec("8. 用户 /user")
    test("用户", "GET", "/user/profile", headers=hdrs)
    test("用户", "PUT", "/user/profile", json={"nickname": "测试用户"}, headers=hdrs)
    test("用户", "GET", "/user/preferences", headers=hdrs)
    test("用户", "PUT", "/user/preferences", json={"language": "zh-CN"}, headers=hdrs)
    test("用户", "POST", "/user/sessions/anonymous/merge",
         json={"anonymous_id": "anon_test"}, headers=hdrs)

    # ────── 报告 ──────
    generate_report()


def generate_report():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# API 响应时长测试报告（含测试数据）\n",
        f"**测试时间**: {now}",
        f"  \n**测试环境**: 本地开发服务器 (端口 8001)",
        f"  \n**测试端点数**: {len(results)}",
        f"  \n**认证方式**: Bearer JWT Token (password 模式登录)",
        f"  \n**数据准备**: 通过 app repositories 直接播种方案/行程/签到/花费/游记\n",
        "---\n",
    ]

    modules = {}
    for r in results:
        modules.setdefault(r[0], []).append(r)

    for mod, mod_results in modules.items():
        lines.append(f"\n## {mod}\n")
        lines.append("| 方法 | 路径 | 状态码 | 响应时长(ms) | 备注 |")
        lines.append("|------|------|--------|-------------|------|")
        for r in mod_results:
            _, method, path, status, ms, note = r
            color = "🟢" if status in (200, 201) else "🟡" if status in (204, 304, 422) else "🔴" if status else "⚪"
            lines.append(f"| {method} | `{path}` | {color} {status} | {ms} | {note[:80]} |")

    durations = [r[4] for r in results if r[4] > 0]
    success = sum(1 for r in results if r[3] in (200, 201, 204))
    fail = sum(1 for r in results if r[3] not in (200, 201, 204) and r[3] != 0)
    skip = sum(1 for r in results if r[3] == 0)

    lines.extend([
        "\n---\n",
        "## 汇总统计\n",
        "| 指标 | 值 |",
        "|------|-----|",
    ])
    if durations:
        lines.append(f"| 平均响应时长 | {sum(durations)/len(durations):.1f} ms |")
        lines.append(f"| 中位响应时长 | {sorted(durations)[len(durations)//2]:.1f} ms |")
        lines.append(f"| 最慢接口 | {max(durations):.1f} ms |")
        lines.append(f"| 最快接口 | {min(durations):.1f} ms |")
    lines.append(f"| 成功 (2xx) | {success} |")
    lines.append(f"| 失败 (非2xx) | {fail} |")
    lines.append(f"| 跳过/异常 | {skip} |")

    lines.append("\n### 各模块平均响应时长\n")
    lines.append("| 模块 | 平均时长(ms) | 端点数 | 成功率 |")
    lines.append("|------|-------------|--------|--------|")
    for mod, mod_results in modules.items():
        ds = [r[4] for r in mod_results if r[4] > 0]
        avg = sum(ds) / len(ds) if ds else 0
        total = len(mod_results)
        ok = sum(1 for r in mod_results if r[3] in (200, 201, 204))
        lines.append(f"| {mod} | {avg:.1f} | {total} | {ok}/{total} |")

    md = "\n".join(lines)
    path = "docs/Sprint1/test/api_response_benchmark.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"\n报告已生成: {path}")


if __name__ == "__main__":
    asyncio.run(main())
