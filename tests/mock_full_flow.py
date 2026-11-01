"""全链路验证：插入 Mock 数据 → DRY 测试各端点"""
import os, sys, json, time, random
os.environ["PYTHONIOENCODING"] = "utf-8"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8765/api/v1"
total = passed = 0
c = None  # httpx client


def test(name, fn):
    global total, passed
    total += 1
    try:
        r = fn()
        body = r.json() if r.text.strip() else {}
        code = body.get("code") if body else None
        ok = code == 0
        if ok:
            passed += 1
            print(f"  [PASS] {name}")
        else:
            print(f"  [FAIL] {name} -> code={code}")
        return body.get("data") if ok else None
    except Exception as e:
        print(f"  [FAIL] {name} -> {e}")
        return None


# ---- 0. 注册 ----
random.seed(time.time())
phone = "1" + str(random.choice([30, 31, 32, 33, 34, 35])) + \
    str(int(time.time() * 1000000))[-8:]
phone = phone[:11]

import httpx

c = httpx.Client()
r = c.post(f"{BASE}/auth/register", json={
    "phone": phone, "password": "test123456", "nickname": "全链路测试"
}, timeout=10)
reg = r.json()
token = reg["data"]["access_token"]
user_id = reg["data"]["user"]["id"]
headers = {"Authorization": f"Bearer {token}"}
print(f"[0] 用户注册 OK: {user_id[:8]}...")

# ---- 1. 插入 Plan + Trip (async ORM) ----
import asyncio
from datetime import date, datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.db.models.base import generate_uuid
from app.db.models.plan import Plan
from app.db.models.trip import TripState

plan_id = generate_uuid()
trip_id = generate_uuid()


async def insert_mock():
    engine = create_async_engine(settings.DATABASE_URL)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        session.add(Plan(
            id=plan_id, user_id=user_id,
            destination="武汉", departure="北京",
            start_date=date(2026, 7, 20), end_date=date(2026, 7, 22),
            budget=5000.0, travelers=2, crowd_type="friends",
            travel_style="balanced", status="completed", total_cost=3500.0,
        ))
        await session.flush()
        session.add(TripState(
            id=trip_id, plan_id=plan_id, user_id=user_id,
            status="active", current_day=1, total_pois=6, checked_in=0,
            started_at=datetime.utcnow(),
            budget_total=5000.0, budget_spent=0.0, budget_remain=5000.0,
        ))
        await session.commit()
    await engine.dispose()


asyncio.run(insert_mock())
print(f"[+] Plan={plan_id[:8]}... Trip={trip_id[:8]}...")

# ============ 签到 ============
print("\n=== 签到 (Checkin) ===")
test("POST checkin (黄鹤楼)", lambda: c.post(f"{BASE}/trips/{trip_id}/checkins", json={
    "poi_type":"attraction","poi_name":"黄鹤楼","source_day":1,
    "lat":30.55,"lng":114.30,"rating":5,"note":"壮观",
    "photos":[{"url":"https://ex.com/hh.jpg"}],
}, headers=headers, timeout=10))

test("POST checkin (热干面)", lambda: c.post(f"{BASE}/trips/{trip_id}/checkins", json={
    "poi_type":"restaurant","poi_name":"蔡林记热干面","source_day":1,
    "rating":4,"actual_cost":15,"note":"正宗",
}, headers=headers, timeout=10))

checkins_data = test("GET checkins", lambda: c.get(f"{BASE}/trips/{trip_id}/checkins", headers=headers, timeout=10))
if checkins_data:
    clist = checkins_data.get("list", [])
    print(f"       -> {len(clist)} 条签到记录")

# ============ 花费 ============
print("\n=== 花费 (Expense) ===")
test("POST expense 门票", lambda: c.post(f"{BASE}/trips/{trip_id}/expenses", json={
    "category":"门票","amount":80,"note":"黄鹤楼"
}, headers=headers, timeout=10))

test("POST expense 餐饮", lambda: c.post(f"{BASE}/trips/{trip_id}/expenses", json={
    "category":"餐饮","amount":45,"note":"热干面"
}, headers=headers, timeout=10))

test("GET expenses", lambda: c.get(f"{BASE}/trips/{trip_id}/expenses", headers=headers, timeout=10))

# ============ 行程进度 & 状态 ============
print("\n=== 行程 (Trip) ===")
progress = test("GET progress", lambda: c.get(f"{BASE}/trips/{trip_id}/progress", headers=headers, timeout=10))
if progress:
    print(f"       day={progress['current_day']} checked={progress['checked_in']}/{progress['total_pois']} "
          f"budget_spent={progress['budget_spent']} pct={progress['progress_pct']}%")

test("PATCH status -> paused", lambda: c.patch(f"{BASE}/trips/{trip_id}", json={"status":"paused"}, headers=headers, timeout=10))
test("PATCH status -> active", lambda: c.patch(f"{BASE}/trips/{trip_id}", json={"status":"active"}, headers=headers, timeout=10))

# ============ 调整 ============
print("\n=== 调整 (Adjustment) ===")
test("POST detect", lambda: c.post(f"{BASE}/trips/{trip_id}/adjustments/detect", json={
    "trigger_type":"weather","trigger_detail":{"rain":1},
    "daily_plan":[],"destination":"武汉"
}, headers=headers, timeout=15))

test("GET adjustments", lambda: c.get(f"{BASE}/trips/{trip_id}/adjustments", headers=headers, timeout=10))

# ============ 提醒 ============
print("\n=== 提醒 (Reminder) ===")
test("GET reminder", lambda: c.get(f"{BASE}/trips/{trip_id}/reminder", headers=headers, timeout=10))

# ============ 照片标注 ============
print("\n=== 照片 (Photo) ===")
test("POST photos/annotate", lambda: c.post(f"{BASE}/trips/{trip_id}/photos/annotate", json={
    "checkin":{"poi_name":"黄鹤楼","photos":[{"url":"https://ex.com/p.jpg"}]}
}, headers=headers, timeout=30))

# ============ 游记 ============
print("\n=== 游记 (Travelogue) ===")
test("POST generate", lambda: c.post(f"{BASE}/travelogues", json={
    "trip_id":trip_id,"style":"diary"
}, headers=headers, timeout=30))

test("GET travelogues", lambda: c.get(f"{BASE}/travelogues", headers=headers, timeout=10))

# ============ 社交素材 ============
print("\n=== 社交素材 (Material) ===")
test("POST materials/generate", lambda: c.post(f"{BASE}/travelogues/materials/generate", json={
    "trip_id":trip_id
}, headers=headers, timeout=30))

test("GET materials", lambda: c.get(f"{BASE}/travelogues/materials", params={"trip_id":trip_id}, headers=headers, timeout=10))

# ============ 分享 ============
print("\n=== 分享 (Share) ===")
r = c.post(f"{BASE}/travelogues/shares", json={
    "target_type":"travelogue","target_id":trip_id
}, headers=headers, timeout=10)
share_code = ""
if r.json().get("code") == 0:
    share_code = r.json()["data"].get("share_code", "")
    print(f"  [PASS] POST shares -> code={share_code}")
    passed += 1
else:
    print(f"  [FAIL] POST shares -> code={r.json().get('code')}")
total += 1

if share_code:
    test("GET share", lambda: c.get(f"{BASE}/travelogues/shares/{share_code}", headers=headers, timeout=10))

# ============ 导出 ============
print("\n=== 导出 (Export) ===")
# Markdown 同步下载
r = c.post(f"{BASE}/plans/{plan_id}/exports", params={"format":"md"}, headers=headers, timeout=10)
if r.status_code == 200 and r.headers.get("content-type", "").startswith("text/markdown"):
    print(f"  [PASS] POST export md ({len(r.content)} bytes)")
    passed += 1
else:
    print(f"  [FAIL] POST export md -> HTTP {r.status_code}")
total += 1

# PDF 异步任务
r = c.post(f"{BASE}/plans/{plan_id}/exports", params={"format":"pdf"}, headers=headers, timeout=10)
task_id = ""
if r.json().get("code") == 0:
    task_id = r.json()["data"].get("task_id", "")
    print(f"  [PASS] POST export pdf -> task_id={task_id[:30]}...")
    passed += 1

    # 轮询任务
    for i in range(8):
        time.sleep(2)
        r2 = c.get(f"{BASE}/tasks/{task_id}", headers=headers, timeout=10)
        if r2.json().get("code") == 0:
            st = r2.json()["data"].get("status")
            if st == "completed":
                total += 1
                r3 = c.get(f"{BASE}/tasks/{task_id}/download", headers=headers, timeout=10)
                if r3.status_code == 200 and len(r3.content) > 100:
                    print(f"  [PASS] GET task/download -> PDF {len(r3.content)} bytes")
                    passed += 1
                else:
                    print(f"  [FAIL] GET task/download -> HTTP {r3.status_code}")
                break
            elif st == "failed":
                print(f"       task failed: {r2.json()['data'].get('error','')}")
                break
else:
    print(f"  [FAIL] POST export pdf -> code={r.json().get('code')}")
total += 1

# ============ 结果 ============
print(f"\n{'='*50}")
print(f"  全链路结果: {passed}/{total} 通过")
print(f"{'='*50}")
