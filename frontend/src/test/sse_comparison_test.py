#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
前后端 SSE 响应对比测试

模拟前端如何解析 SSE 流，并直接与后端原始响应对比。

测试内容:
1. 模拟前端登录/创建会话/发送消息/解析 SSE
2. 捕获后端原始 SSE 事件流
3. 按前端 chatStore.handleSSEEvent() 的逻辑解析
4. 检查前端是否能完整渲染每个事件

前端 SSE 解析逻辑参考: frontend/src/store/chatStore.ts -> handleSSEEvent()
"""

import json
import sys
import time
import httpx

BASE_URL = "http://localhost:8000/api/v1"

# 测试问题（多个不同场景）
TEST_QUESTIONS = [
    "武汉出发去北京3天5000",
    "我想去三亚玩",
    "你好",
]

# ============================================================
# 工具函数
# ============================================================

def request_json(method, path, **kwargs):
    """发起 JSON 请求并统一处理错误"""
    url = "%s%s" % (BASE_URL, path)
    try:
        response = httpx.request(method, url, timeout=30, **kwargs)
    except httpx.RequestError as exc:
        print("[FAIL] 请求失败: %s %s - %s" % (method, url, str(exc)))
        return None

    try:
        payload = response.json()
    except json.JSONDecodeError:
        print("[FAIL] 非 JSON 响应: HTTP %d" % response.status_code)
        print("   Body: %s" % response.text[:300])
        return None

    if response.status_code >= 400:
        print("[FAIL] HTTP %d: %s" % (response.status_code, json.dumps(payload, ensure_ascii=False)[:200]))
        return None

    return payload


def simulate_frontend_sse_parse(events):
    """
    模拟前端的 handleSSEEvent() 逻辑，解析 SSE 事件并构建消息列表。
    """
    messages = []
    plan_data = {}

    for evt, data in events:
        if evt == "step_start":
            step = data.get("step", "")
            label = data.get("label", "[%s]" % step)
            messages.append({
                "type": "plan_progress",
                "step": step,
                "content": label,
                "metadata": {"step": step},
                "role": "system",
            })

        elif evt == "message":
            messages.append({
                "type": "text",
                "role": "assistant",
                "content": data.get("content", ""),
                "message_type": data.get("message_type", "text"),
                "suggestions": data.get("suggestions"),
            })

        elif evt == "progress":
            percent = data.get("percent", 0)
            msg = data.get("message", "")
            found = False
            for m in reversed(messages):
                if m["type"] == "plan_progress" and not m.get("completed"):
                    m["content"] = msg
                    m["percent"] = percent
                    found = True
                    break
            if not found:
                messages.append({
                    "type": "plan_progress",
                    "content": msg,
                    "percent": percent,
                    "role": "system",
                })

        elif evt == "step_end":
            step = data.get("step", "")
            for m in reversed(messages):
                if m.get("step") == step:
                    m["completed"] = True
                    break

        elif evt == "error":
            messages.append({
                "type": "error",
                "role": "system",
                "content": data.get("message", "未知错误"),
            })

        elif evt == "done":
            status = data.get("status")
            if status == "waiting_input":
                messages.append({
                    "type": "system",
                    "role": "system",
                    "content": "[等待用户继续输入]",
                })
            else:
                summary = data.get("summary", {})
                plan_data = summary
                plan_text = _generate_plan_text(summary)
                messages.append({
                    "type": "plan_result",
                    "role": "assistant",
                    "content": plan_text,
                    "metadata": {
                        "plan_id": data.get("plan_id"),
                        "session_id": data.get("session_id"),
                        "summary": summary,
                    },
                })

    return {"messages": messages, "plan_data": plan_data}


def _generate_plan_text(summary):
    """模拟前端生成方案文本的逻辑 (chatStore.ts lines 385-401)"""
    if not summary:
        return "[方案已生成]"

    itinerary = summary.get("daily_itinerary", []) or summary.get("daily_plan", [])
    if not itinerary:
        return "[方案已生成，您可以在右侧预览详情]"

    text = "[为您规划了%s%d日游：" % (summary.get("destination", ""), summary.get("days", 0))
    for day in itinerary:
        acts = day.get("attractions", []) or day.get("activities", [])
        meals = day.get("meals", [])
        names = "、".join([a.get("name", "") for a in acts if a.get("name")])
        text += "[第%d天：%s" % (day.get("day", 0), names)
        if meals:
            text += " | " + "、".join([m.get("restaurant", "") for m in meals])
        text += "]"

    budget = summary.get("budget", {})
    text += "[总预算¥%d，预估花费¥%d]" % (budget.get("total_budget", 0), budget.get("actual_total", 0))
    return text


def print_sse_summary(events):
    """打印 SSE 事件概要"""
    event_counts = {}
    for evt, _ in events:
        event_counts[evt] = event_counts.get(evt, 0) + 1

    print("  [EVENTS] 统计: %s (总计 %d 个事件)" % (json.dumps(event_counts, ensure_ascii=False), len(events)))

    for i, (evt, data) in enumerate(events):
        if evt == "step_start":
            print("    [%d] step_start: %s -- %s" % (i+1, data.get('step'), data.get('label')))
        elif evt == "step_end":
            print("    [%d] step_end: %s" % (i+1, data.get('step')))
        elif evt == "progress":
            print("    [%d] progress: %d%% -- %s" % (i+1, data.get('percent', 0), data.get('message')))
        elif evt == "message":
            content = data.get("content", "")
            msg_type = data.get("message_type", "text")
            preview = content[:60] + ("..." if len(content) > 60 else "")
            print("    [%d] message (%s): %s" % (i+1, msg_type, preview))
        elif evt == "error":
            print("    [%d] error: %s" % (i+1, data.get('message')))
        elif evt == "done":
            status = data.get("status", "complete")
            if status == "waiting_input":
                print("    [%d] done: waiting_input" % (i+1))
            else:
                summary = data.get("summary", {})
                dest = summary.get("destination", "?")
                days = summary.get("days", 0)
                budget = summary.get("budget", {})
                print("    [%d] done: 方案完成 -- %s %d天 Y%d/Y%d" % (
                    i+1, dest, days, budget.get('actual_total', 0), budget.get('total_budget', 0)))


def check_frontend_renderability(frontend_result):
    """
    检查前端是否能完整渲染 SSE 响应。
    返回所有发现的问题列表。
    """
    issues = []
    messages = frontend_result.get("messages", [])
    plan_data = frontend_result.get("plan_data", {})

    if not messages:
        issues.append("[RENDER] 无任何消息生成，前端完全无法渲染")
        return issues

    # 检查 1: 是否有抛出 error 事件
    error_msgs = [m for m in messages if m.get("type") == "error"]
    if error_msgs:
        for em in error_msgs:
            issues.append("[RENDER] 包含错误消息: %s" % em.get('content'))

    # 检查 2: 是否有 assistant 回复（ChatMessage.vue 渲染）
    assistant_msgs = [m for m in messages if m.get("role") == "assistant" and m.get("type") == "text"]
    if not assistant_msgs:
        issues.append("[RENDER] 没有 assistant text 消息（聊天气泡无法显示）")
    else:
        for am in assistant_msgs:
            content = am.get("content", "")
            if len(content) == 0:
                issues.append("[RENDER] assistant 消息内容为空")
            msg_type = am.get("message_type", "")
            if msg_type not in ("text", "markdown", "plan_result"):
                issues.append("[RENDER] 未知消息类型: %s" % msg_type)

    # 检查 3: plan_result 消息的完整性
    plan_result_msgs = [m for m in messages if m.get("type") == "plan_result"]
    if plan_result_msgs:
        pr = plan_result_msgs[-1]
        meta = pr.get("metadata", {})
        if not meta.get("plan_id"):
            issues.append("[RENDER] plan_result 缺少 plan_id")
        if not meta.get("summary"):
            issues.append("[RENDER] plan_result 缺少 summary 数据")
        if plan_data:
            if not plan_data.get("daily_itinerary") and not plan_data.get("daily_plan"):
                issues.append("[RENDER] 方案数据缺少 daily_itinerary/daily_plan")
            if not plan_data.get("budget"):
                issues.append("[RENDER] 方案数据缺少 budget")

    # 检查 4: 进度事件是否覆盖 0-100%
    progress_events = [m for m in messages if m.get("percent") is not None]
    if progress_events:
        max_percent = max(m.get("percent", 0) for m in progress_events)
        if max_percent < 100:
            issues.append("[RENDER] 进度未到 100%%（最大 %d%%）" % max_percent)

    return issues


# ============================================================
# 主要测试流程
# ============================================================

def test_flow(label, question):
    """测试完整的 登录->创建会话->发送消息->SSE 解析 流程"""
    print("")
    print("=" * 60)
    print("[TEST] %s" % label)
    print("[TEST] Q: %s" % question)
    print("=" * 60)

    # ---- 第1步: 登录 ----
    print("")
    print("[Step 1] 登录获取 Token...")
    result = request_json(
        "POST",
        "/auth/sessions",
        json={"method": "phone", "phone": "13700001111", "code": "123456"},
    )
    if not result:
        print("  [FAIL] 登录失败，跳过后续测试")
        return None, None

    token = result["data"]["access_token"]
    user = result["data"]["user"]
    print("  [OK] 登录成功: %s (ID: %s...)" % (user.get('nickname', '?'), user.get('id', '?')[:8]))

    # ---- 第2步: 创建会话 ----
    print("")
    print("[Step 2] 创建会话...")
    result = request_json(
        "POST",
        "/chat/sessions",
        headers={"Authorization": "Bearer %s" % token},
        json={},
    )
    if not result:
        print("  [FAIL] 创建会话失败")
        return None, None

    session_id = result["data"]["id"]
    print("  [OK] 会话创建成功: %s..." % session_id[:8])

    # ---- 第3步: 发送消息并获取 SSE 流 ----
    print("")
    print("[Step 3] 发送消息并接收 SSE 流...")
    print("  (Pipeline 可能需要 60-80 秒，请耐心等待...)")
    start_time = time.time()

    raw_events = None
    frontend_result = None

    with httpx.stream(
        "POST",
        "%s/chat/sessions/%s/messages" % (BASE_URL, session_id),
        headers={"Authorization": "Bearer %s" % token},
        json={"content": question},
        timeout=300,
    ) as response:
        if response.status_code >= 400:
            print("  [FAIL] SSE 流 HTTP %d: %s" % (response.status_code, response.read().decode()[:200]))
            return None, None

        print("  [OK] SSE 连接建立成功 (HTTP 200)")

        # 方式 A: 模拟前端解析 SSE
        print("")
        print("  -- 方式 A: 模拟前端解析 SSE --")
        current_event = None
        current_data = ""
        raw_events = []

        for line in response.iter_lines():
            line = line.strip()
            if line.startswith("event: "):
                current_event = line[7:].strip()
            elif line.startswith("data: "):
                current_data = line[6:]
            elif line == "" and current_event and current_data:
                try:
                    parsed = json.loads(current_data)
                    raw_events.append((current_event, parsed))
                except json.JSONDecodeError:
                    pass
                current_event = None
                current_data = ""

        elapsed = time.time() - start_time
        print("  [TIME] %.1f 秒" % elapsed)
        print("  [DATA] 原始 SSE 事件数: %d" % len(raw_events))

        # 模拟前端解析
        frontend_result = simulate_frontend_sse_parse(raw_events)
        frontend_msgs = frontend_result.get("messages", [])
        plan = frontend_result.get("plan_data", {})
        print("  [DATA] 前端解析后消息数: %d" % len(frontend_msgs))
        if plan:
            dest = plan.get("destination", "?")
            days = plan.get("days", 0)
            budget = plan.get("budget", {})
            actual = budget.get("actual_total", 0)
            total_b = budget.get("total_budget", 0)
            print("  [DATA] 方案数据: %s %d天 Y%d/Y%d" % (dest, days, actual, total_b))

        # 打印 SSE 事件概要
        print_sse_summary(raw_events)

        # 检查前端渲染完整性
        issues = check_frontend_renderability(frontend_result)
        if issues:
            print("")
            print("  [ISSUES] 前端渲染问题 (%d 项):" % len(issues))
            for issue in issues:
                print("    %s" % issue)
        else:
            print("")
            print("  [OK] 前端渲染检查通过，无发现问题")

    return raw_events, frontend_result


def compare_responses(responses):
    """对比不同问题的回复"""
    print("")
    print("=" * 60)
    print("[COMPARE] 多场景回复对比")
    print("=" * 60)

    for q, result in responses.items():
        if result is None:
            print("  [SKIP] %s... -> 测试失败" % q[:30])
            continue

        events, frontend = result
        msgs = frontend.get("messages", [])
        plan = frontend.get("plan_data", {})

        event_types = {}
        for evt, _ in events:
            event_types[evt] = event_types.get(evt, 0) + 1

        plan_result_msgs = [m for m in msgs if m.get("type") == "plan_result"]
        assistant_msgs = [m for m in msgs if m.get("role") == "assistant" and m.get("type") == "text"]

        print("")
        print("  [Q] %s..." % q[:40])
        print("     SSE 事件: %s" % json.dumps(event_types, ensure_ascii=False))
        print("     前端消息: %d 条 (assistant=%d, plan_result=%d)" % (
            len(msgs), len(assistant_msgs), len(plan_result_msgs)))
        if plan:
            dest = plan.get("destination", "?")
            days = plan.get("days", "?")
            budget = plan.get("budget", {})
            actual = budget.get("actual_total", 0)
            total_b = budget.get("total_budget", 0)
            print("     方案: %s %s天 Y%d/Y%d" % (dest, days, actual, total_b))

        issues = check_frontend_renderability(frontend)
        if issues:
            print("     问题: %s" % "; ".join(issues))


# ============================================================
# 主入口
# ============================================================

if __name__ == "__main__":
    # 先测试健康检查
    print("[INIT] 健康检查...")
    health = request_json("GET", "/health")
    if health and health.get("code") == 0:
        print("  [OK] 后端健康: %s" % json.dumps(health['data'], ensure_ascii=False))
    else:
        print("  [FAIL] 后端不可用，请确保服务已启动")
        sys.exit(1)

    # 测试所有问题
    results = {}
    for question in TEST_QUESTIONS:
        events, frontend = test_flow("[Q] %s" % question[:30], question)
        results[question] = (events, frontend)

    # 对比不同问题的回复
    compare_responses(results)

    print("")
    print("=" * 60)
    print("[DONE] 全部测试完成")
    print("=" * 60)
