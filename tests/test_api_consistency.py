"""
前端-后端 API 一致性测试

测试两条路径：
- 路径 A（完整链路）：模拟前端 SSE 解析逻辑 --> 验证渲染完整性
- 路径 B（纯后端）：直接发 HTTP 请求 --> 捕获原始 SSE 响应
- 对比：两条路径的事件序列和消息内容是否一致

后端实际 SSE 事件流包含：
  step_start -> message_delta(多个流式片断) -> message(完整内容) -> step_end -> done

用法：
  1. 先启动后端: python main.py
  2. 运行本脚本: python tests/test_api_consistency.py
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Any

import httpx

# ---- 配置 ----
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
TEST_PHONE = "13800000001"
TEST_PASSWORD = "test123456"

# 测试问题
TEST_CASES = [
    {"id": "TC1", "desc": "闲聊问候", "content": "你好"},
    {"id": "TC2", "desc": "简单旅行规划", "content": "我想去北京玩3天"},
]


# ==============================================================
# 路径 B：纯后端 API 调用 --> 捕获原始 SSE
# ==============================================================

class RawSSECollector:
    """收集原始 SSE 事件"""

    def __init__(self):
        self.events: list[dict] = []
        self.raw_text: str = ""

    def parse(self, text: str) -> list[dict]:
        self.raw_text = text
        self.events = []
        lines = text.split("\n")
        current_event: str | None = None
        current_data: str = ""

        for line in lines:
            if line.startswith("event: "):
                current_event = line[7:].strip()
            elif line.startswith("data: "):
                current_data = line[6:]
            elif line == "" and current_event and current_data:
                try:
                    parsed = json.loads(current_data)
                except json.JSONDecodeError:
                    parsed = {"raw": current_data}
                self.events.append({
                    "event": current_event,
                    "data": parsed,
                })
                current_event = None
                current_data = ""

        return self.events


async def path_b_send_message(client: httpx.AsyncClient, session_id: str, content: str) -> RawSSECollector:
    """
    路径 B：直接发 HTTP POST，获取原始 SSE 响应文本。
    """
    collector = RawSSECollector()
    response = await client.post(
        f"{BASE_URL}/chat/sessions/{session_id}/messages",
        json={"content": content},
    )
    response.raise_for_status()
    text = response.text
    collector.parse(text)
    return collector


# ==============================================================
# 路径 A：模拟前端 SSE 解析逻辑（复刻 chatStore.ts）
# ==============================================================

class FrontendSSESimulator:
    """
    模拟前端的 SSE 事件处理逻辑（复刻 chatStore.ts 的 handleSSEEvent）。
    根据实测，后端发送的 SSE 事件类型包括：
      step_start, message_delta, message, progress, step_end, error, done

    前端只处理：step_start, message, progress, step_end, error, done
    message_delta 被前端忽略（前端的 message 事件拿到的是完整内容）。
    """

    def __init__(self):
        self.messages: list[dict] = []
        self.current_plan: dict | None = None
        self.stream_done: bool = False
        self.done_status: str | None = None

    def handle_event(self, event: str, data: dict):
        """复刻 chatStore.ts 的 handleSSEEvent 逻辑"""

        if event == "step_start":
            self.messages.append({
                "role": "system",
                "message_type": "plan_progress",
                "content": data.get("label", "Processing..."),
                "metadata": {"step": data.get("step", ""), "completed": False},
            })

        elif event == "message":
            msg = {
                "role": data.get("role", "assistant"),
                "content": data.get("content", ""),
                "message_type": data.get("message_type", "text"),
                "metadata": {},
            }
            if "suggestions" in data:
                msg["metadata"]["suggestions"] = data["suggestions"]
            self.messages.append(msg)

        elif event == "progress":
            found = False
            for m in reversed(self.messages):
                if m["message_type"] == "plan_progress":
                    m["content"] = data.get("message", m["content"])
                    m.setdefault("metadata", {})["percent"] = data.get("percent", 0)
                    found = True
                    break
            if not found:
                self.messages.append({
                    "role": "system",
                    "message_type": "plan_progress",
                    "content": data.get("message", ""),
                    "metadata": {"percent": data.get("percent", 0)},
                })

        elif event == "step_end":
            step = data.get("step", "")
            for m in reversed(self.messages):
                if m.get("metadata", {}).get("step") == step:
                    m["metadata"]["completed"] = True
                    break

        elif event == "error":
            self.messages.append({
                "role": "system",
                "message_type": "text",
                "content": data.get("message", "Unknown error"),
            })

        elif event == "done":
            self.stream_done = True
            status = data.get("status", "")
            self.done_status = status

            if status == "waiting_input":
                pass
            else:
                summary = data.get("summary", {})
                plan_text = self._build_plan_summary(summary)
                self.messages.append({
                    "role": "assistant",
                    "message_type": "plan_result",
                    "content": plan_text,
                    "metadata": {
                        "plan_id": data.get("plan_id", ""),
                        "session_id": data.get("session_id", ""),
                        "summary": summary,
                    },
                })
                self.current_plan = summary

    def _build_plan_summary(self, summary: dict) -> str:
        destination = summary.get("destination", summary.get("origin", "未知目的地"))
        days = summary.get("days", 0)
        lines = ["## 旅行方案已生成！\n"]
        lines.append(f"**目的地**：{destination}")
        if days:
            lines.append(f"**天数**：{days} 天")
        budget = summary.get("budget", {})
        if budget:
            total = budget.get("total_budget", 0) or budget.get("actual_total", 0)
            if total:
                lines.append(f"**预算**：￥{total:,.0f}")
        return "\n".join(lines)

    def run_events(self, events: list[dict]):
        for evt in events:
            self.handle_event(evt["event"], evt["data"])

    def validate_render_completeness(self, test_case_id: str) -> list[str]:
        """
        验证前端渲染完整性：
        - 所有事件都被正确处理
        - 消息列表非空
        - stream_done 已触发
        - 无 pending 状态
        """
        issues: list[str] = []

        if not self.stream_done:
            issues.append("[FAIL] stream_done 未触发，流未完成")

        if len(self.messages) == 0:
            issues.append("[FAIL] 消息列表为空，没有任何渲染内容")

        progress_msgs = [m for m in self.messages if m["message_type"] == "plan_progress"]
        if progress_msgs:
            for pm in progress_msgs:
                if not pm["metadata"].get("completed", True) and pm["metadata"].get("step"):
                    issues.append(f"[WARN] 步骤 [{pm['metadata'].get('step')}] 未收到 step_end")

        for i, m in enumerate(self.messages):
            if not m["content"] and m["message_type"] != "plan_progress":
                issues.append(f"[WARN] 第 {i+1} 条消息内容为空 (type={m['message_type']})")

        return issues


# ==============================================================
# 比较器
# ==============================================================

def compare_results(tc_id: str, desc: str, path_a: FrontendSSESimulator, path_b: RawSSECollector) -> dict:
    """
    比较两条路径的结果。
    关键洞察：path_b 接收了所有事件（含 message_delta），
    path_a 只处理前端关心的部分事件。
    核心对比的是 message 事件的内容一致性。
    """
    comparison = {
        "test_case_id": tc_id,
        "test_case_desc": desc,
        "path_b_raw_event_count": len(path_b.events),
        "path_b_non_delta_events": len([e for e in path_b.events if e["event"] != "message_delta"]),
        "path_a_message_count": len(path_a.messages),
        "differences": [],
        "match": True,
    }

    path_b_messages = [e for e in path_b.events if e["event"] == "message"]
    path_a_text_msgs = [m for m in path_a.messages if m["message_type"] == "text"]

    if len(path_b_messages) != len(path_a_text_msgs):
        comparison["differences"].append(
            f"message 事件数不一致: path_b={len(path_b_messages)}, path_a={len(path_a_text_msgs)}"
        )
        comparison["match"] = False

    for i, (b_msg, a_msg) in enumerate(zip(path_b_messages, path_a_text_msgs)):
        b_content = b_msg["data"].get("content", "")
        a_content = a_msg["content"]
        if b_content.strip() != a_content.strip():
            comparison["differences"].append(
                f"message #{i} 内容不一致:\n  path_b: {b_content[:100]}...\n  path_a: {a_content[:100]}..."
            )
            comparison["match"] = False

    path_b_done = [e for e in path_b.events if e["event"] == "done"]
    if path_b_done:
        b_status = path_b_done[0]["data"].get("status", "")
        a_status = path_a.done_status or ""
        if b_status != a_status:
            comparison["differences"].append(
                f"done status 不一致: path_b={b_status}, path_a={a_status}"
            )
            comparison["match"] = False

    return comparison


# ==============================================================
# 认证工具
# ==============================================================

async def register_and_login(client: httpx.AsyncClient) -> dict:
    """注册测试用户并登录，返回 token 信息"""
    # 先尝试注册
    reg_resp = await client.post(
        f"{BASE_URL}/auth/register",
        json={"phone": TEST_PHONE, "password": TEST_PASSWORD, "nickname": "测试用户"},
    )
    reg_data = reg_resp.json()

    if reg_data.get("code") == 0 and reg_data.get("data"):
        token_data = reg_data["data"]
        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data["refresh_token"],
            "user_id": token_data["user"]["id"],
        }

    # 如果已注册，尝试登录
    login_resp = await client.post(
        f"{BASE_URL}/auth/sessions",
        json={"method": "password", "phone": TEST_PHONE, "password": TEST_PASSWORD},
    )
    login_data = login_resp.json()
    if login_data.get("code") == 0 and login_data.get("data"):
        token_data = login_data["data"]
        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data["refresh_token"],
            "user_id": token_data["user"]["id"],
        }

    raise RuntimeError(f"认证失败: {reg_data}")


async def create_session(client: httpx.AsyncClient, token: str) -> str:
    """创建新的聊天会话，返回 session_id"""
    resp = await client.post(
        f"{BASE_URL}/chat/sessions",
        json={"title": "API 一致性测试"},
        headers={"Authorization": f"Bearer {token}"},
    )
    data = resp.json()
    assert data["code"] == 0, f"创建会话失败: {data}"
    return data["data"]["id"]


# ==============================================================
# 主流程
# ==============================================================

async def run_test():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_lines = [
        f"# 前端-后端 API 一致性测试报告\n",
        f"**测试时间**：{timestamp}",
        f"**后端地址**：{BASE_URL}",
        f"**测试用户**：{TEST_PHONE}",
        "",
        "---",
        "",
    ]

    async with httpx.AsyncClient(timeout=300.0) as client:
        # ---- 认证 ----
        print("[INFO] 认证中...")
        auth = await register_and_login(client)
        token = auth["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}
        client.headers.update(auth_headers)
        print(f"[INFO] 用户 ID: {auth['user_id']}")

        for tc in TEST_CASES:
            tc_id = tc["id"]
            tc_desc = tc["desc"]
            content = tc["content"]
            print(f"\n{'='*60}")
            print(f"[{tc_id}] {tc_desc}: \"{content}\"")
            print(f"{'='*60}")

            # ---- 创建新会话 ----
            session_id = await create_session(client, token)
            print(f"[INFO] 会话 ID: {session_id}")

            # ======== 路径 B：纯后端调用 ========
            print("[INFO] 路径 B: 发送请求到后端 API...")
            start_b = time.time()
            collector = await path_b_send_message(client, session_id, content)
            elapsed_b = time.time() - start_b

            print(f"[INFO] 路径 B 完成 ({elapsed_b:.1f}s), 事件数: {len(collector.events)}")
            for evt in collector.events:
                evt_type = evt["event"]
                evt_preview = json.dumps(evt["data"], ensure_ascii=False)[:120]
                print(f"  - event: {evt_type} | data: {evt_preview}...")

            # ======== 路径 A：模拟前端渲染 ========
            print("[INFO] 路径 A: 模拟前端 SSE 解析...")
            simulator = FrontendSSESimulator()
            simulator.run_events(collector.events)

            print(f"[INFO] 路径 A 渲染结果: {len(simulator.messages)} 条消息")
            for msg in simulator.messages:
                print(f"  - type: {msg['message_type']}, role: {msg['role']}, content: {msg['content'][:80]}...")
            print(f"  - stream_done: {simulator.stream_done}, done_status: {simulator.done_status}")

            # ---- 验证渲染完整性 ----
            issues = simulator.validate_render_completeness(tc_id)
            if issues:
                print(f"[WARN] 渲染问题:")
                for issue in issues:
                    print(f"  {issue}")
            else:
                print(f"[OK] 渲染完整性检查通过 [v]")

            # ---- 对比结果 ----
            comparison = compare_results(tc_id, tc_desc, simulator, collector)
            status = "[MATCH] 完全一致" if comparison["match"] else "[DIFF] 存在差异"
            print(f"[RESULT] {status}")

            # ---- 收集报告 ----
            report_lines.append(f"## {tc_id}: {tc_desc}")
            report_lines.append("")
            report_lines.append(f"**问题**：\"{content}\"")
            report_lines.append(f"**会话 ID**：`{session_id}`")
            report_lines.append(f"**路径 B 耗时**：{elapsed_b:.1f}s")
            report_lines.append("")

            report_lines.append("### 路径 B - 原始 SSE 事件序列")
            report_lines.append("")
            report_lines.append("| # | 事件类型 | 数据预览 |")
            report_lines.append("|---|---------|---------|")
            for i, evt in enumerate(collector.events):
                preview = json.dumps(evt["data"], ensure_ascii=False)[:100]
                report_lines.append(f"| {i+1} | `{evt['event']}` | {preview} |")
            report_lines.append("")

            report_lines.append("### 路径 A - 模拟前端消息列表")
            report_lines.append("")
            report_lines.append("| # | 类型 | 角色 | 内容摘要 |")
            report_lines.append("|---|------|------|---------|")
            for i, msg in enumerate(simulator.messages):
                content_preview = msg["content"][:80] if msg["content"] else "(empty)"
                report_lines.append(
                    f"| {i+1} | `{msg['message_type']}` | {msg['role']} | {content_preview} |"
                )
            report_lines.append("")

            report_lines.append("### 渲染验证")
            report_lines.append("")
            if issues:
                report_lines.append("**[WARN] 发现问题：**")
                for issue in issues:
                    report_lines.append(f"- {issue}")
            else:
                report_lines.append("**[OK] 所有渲染检查通过**")
            report_lines.append("")

            report_lines.append("### 一致性对比")
            report_lines.append("")
            report_lines.append(f"- **状态**：{status}")
            report_lines.append(f"- **事件数**（Path B）：{comparison['path_b_raw_event_count']}")
            report_lines.append(f"- **消息数**（Path A）：{comparison['path_a_message_count']}")
            if comparison["differences"]:
                report_lines.append("- **差异详情**：")
                for diff in comparison["differences"]:
                    report_lines.append(f"  - {diff}")
            report_lines.append("")
            report_lines.append("---")
            report_lines.append("")

        # ---- 全局汇总 ----
        report_lines.append("## 全局汇总")
        report_lines.append("")
        report_lines.append(f"- **测试用例数**：{len(TEST_CASES)}")
        report_lines.append(f"- **测试时间**：{timestamp}")
        report_lines.append(f"- **后端地址**：{BASE_URL}")
        report_lines.append("")

    # ---- 写报告 ----
    report_path = os.path.join(os.path.dirname(__file__), "..", "docs", "reports", "api-consistency-test-report.md")
    report_path = os.path.abspath(report_path)
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print(f"\n[INFO] 测试报告已保存: {report_path}")
    return report_path


if __name__ == "__main__":
    result = asyncio.run(run_test())
    print(f"\n完成！报告：{result}")
