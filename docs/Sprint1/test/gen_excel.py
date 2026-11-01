#!/usr/bin/env python3
"""将 API 测试报告转成 Excel 表格文件"""

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

# ========== 测试数据 ==========
HEADER = ["测试时间", "测试环境", "测试端点数", "认证方式"]
META = ["2026-07-15 10:03:01", "本地开发服务器 (端口 8001)", 59, "Bearer JWT Token"]

# ---- 所有接口 ----
ENDPOINTS = [
    # (模块, 方法, 路径, 状态码, 响应时长ms, 说明)
    # 认证
    ("认证", "POST", "/auth/sms-codes", 200, 413.0, "发送短信验证码"),
    ("认证", "POST", "/auth/sessions", 200, 580.3, "登录（密码模式）"),
    ("认证", "POST", "/auth/tokens", 200, 396.0, "刷新 Token"),
    ("认证", "DELETE", "/auth/sessions/current", 200, 358.4, "登出"),
    # 聊天
    ("聊天", "POST", "/chat/sessions", 200, 359.3, "创建聊天会话"),
    ("聊天", "GET", "/chat/sessions", 200, 396.0, "会话列表"),
    ("聊天", "PATCH", "/chat/sessions/{session_id}", 200, 371.0, "更新会话"),
    ("聊天", "POST", "/chat/sessions/{session_id}/messages", 200, 2230.6, "发送消息（SSE 流）"),
    ("聊天", "GET", "/chat/sessions/{session_id}/messages", 200, 354.2, "获取消息历史"),
    ("聊天", "GET", "/chat/sessions/{session_id}/plans", 200, 384.3, "列出会话方案"),
    ("聊天", "GET", "/chat/sessions/{session_id}/stream", 200, 2011.3, "SSE 流式返回 Agent 结果"),
    ("聊天", "DELETE", "/chat/sessions/{session_id}", 200, 351.7, "删除会话"),
    # 方案
    ("方案", "POST", "/plans", 200, 0.2, "触发方案生成（SSE Mock）"),
    ("方案", "GET", "/plans", 200, 359.2, "方案列表"),
    ("方案", "GET", "/plans/{plan_id}", 200, 357.7, "方案详情"),
    ("方案", "PATCH", "/plans/{plan_id}", 200, 0.1, "局部修改方案（SSE Mock）"),
    ("方案", "POST", "/plans/{plan_id}/generations", 200, 0.2, "重新生成方案（SSE Mock）"),
    ("方案", "POST", "/plans/{plan_id}/exports", 200, 368.8, "导出 Markdown"),
    ("方案", "POST", "/plans/{plan_id}/shares", 200, 359.8, "分享方案"),
    ("方案", "POST", "/plans/{plan_id}/favorites", 200, 368.6, "收藏/取消收藏"),
    # 行程
    ("行程", "GET", "/trips", 200, 374.5, "我的行程列表"),
    ("行程", "POST", "/trips", 200, 367.9, "从方案创建行程"),
    ("行程", "GET", "/trips/{trip_id}", 200, 366.0, "行程详情"),
    ("行程", "PATCH", "/trips/{trip_id}", 200, 380.0, "更新状态（暂停/继续）"),
    ("行程", "PATCH", "/trips/{trip_id}", 200, 373.1, "更新状态（活跃）"),
    ("行程", "GET", "/trips/{trip_id}/progress", 200, 365.4, "实时进度"),
    ("行程", "POST", "/trips/{trip_id}/checkins", 200, 385.1, "签到"),
    ("行程", "GET", "/trips/{trip_id}/checkins", 200, 363.7, "签到记录"),
    ("行程", "POST", "/trips/{trip_id}/expenses", 200, 372.2, "记录花费"),
    ("行程", "GET", "/trips/{trip_id}/expenses", 200, 374.8, "花费明细"),
    ("行程", "POST", "/trips/{trip_id}/adjustments/detect", 200, 2707.9, "异常检测生成调整"),
    ("行程", "GET", "/trips/{trip_id}/adjustments", 200, 363.3, "调整历史"),
    ("行程", "GET", "/trips/{trip_id}/reminder", 200, 2752.3, "次日提醒"),
    ("行程", "POST", "/trips/{trip_id}/photos/annotate", 200, 2758.3, "AI 照片标注"),
    # 数据
    ("数据", "GET", "/data/cities", 200, 356.4, "热门城市/搜索"),
    ("数据", "GET", "/data/cities?keyword=北京", 200, 384.2, "城市搜索"),
    ("数据", "GET", "/data/attractions?city=北京", 200, 366.6, "景点列表"),
    ("数据", "GET", "/data/attractions/{id}", 200, 378.6, "景点详情"),
    ("数据", "GET", "/data/restaurants?city=北京", 200, 373.3, "餐厅列表"),
    ("数据", "GET", "/data/hotels?city=北京", 200, 377.9, "酒店列表"),
    ("数据", "GET", "/data/weather?city=北京&date=2026-07-16", 200, 380.2, "天气查询"),
    # 运维
    ("运维", "GET", "/health", 200, 17.8, "健康检查"),
    ("运维", "GET", "/tasks/{task_id}", 200, 388.2, "异步导出任务状态"),
    ("运维", "GET", "/tasks/{task_id}/download", 200, 375.7, "下载导出文件"),
    # 游记
    ("游记", "GET", "/travelogues", 200, 387.7, "游记列表（公开已发布）"),
    ("游记", "POST", "/travelogues", 200, 6276.7, "生成游记（LLM 润色）"),
    ("游记", "GET", "/travelogues/{travelogue_id}", 200, 374.6, "游记详情"),
    ("游记", "PATCH", "/travelogues/{travelogue_id}", 200, 382.1, "编辑游记"),
    ("游记", "POST", "/travelogues/{travelogue_id}/publish", 200, 348.5, "发布游记"),
    ("游记", "GET", "/travelogues/materials", 200, 370.8, "社交素材列表"),
    ("游记", "POST", "/travelogues/materials/generate", 200, 2221.9, "一键生成社交素材"),
    ("游记", "POST", "/travelogues/shares", 200, 354.9, "分享链接"),
    ("游记", "GET", "/travelogues/shares/{share_code}", 200, 363.4, "通过短码获取分享"),
    ("游记", "DELETE", "/travelogues/{travelogue_id}", 200, 361.5, "删除游记"),
    # 用户
    ("用户", "GET", "/user/profile", 200, 368.4, "获取用户资料"),
    ("用户", "PUT", "/user/profile", 200, 381.5, "更新用户资料"),
    ("用户", "GET", "/user/preferences", 200, 353.1, "获取偏好配置"),
    ("用户", "PUT", "/user/preferences", 200, 363.4, "更新偏好配置"),
    ("用户", "POST", "/user/sessions/anonymous/merge", 200, 372.3, "匿名数据合并"),
]

# ---- 模块汇总 ----
MODULE_SUMMARY = {
    "认证": {"count": 4, "avg": 436.9},
    "聊天": {"count": 8, "avg": 807.3},
    "方案": {"count": 8, "avg": 226.8},
    "行程": {"count": 14, "avg": 878.9},
    "数据": {"count": 7, "avg": 373.9},
    "运维": {"count": 3, "avg": 260.6},
    "游记": {"count": 10, "avg": 1144.2},
    "用户": {"count": 5, "avg": 367.7},
}


def build_workbook():
    wb = Workbook()

    # ── 样式 ──
    header_font = Font(name="微软雅黑", bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill("solid", fgColor="4472C4")
    header_align = Alignment(horizontal="center", vertical="center")
    cell_font = Font(name="微软雅黑", size=10)
    cell_align = Alignment(vertical="center")
    center_align = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin"),
    )
    green_fill = PatternFill("solid", fgColor="E2EFDA")
    blue_fill = PatternFill("solid", fgColor="D6E4F0")

    def style_header(ws, row, cols):
        for c in range(1, cols + 1):
            cell = ws.cell(row=row, column=c)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align
            cell.border = thin_border

    def style_row(ws, row, cols, fill=None):
        for c in range(1, cols + 1):
            cell = ws.cell(row=row, column=c)
            cell.font = cell_font
            cell.alignment = cell_align
            cell.border = thin_border
            if fill:
                cell.fill = fill

    # ═══════════════════════════════════════
    # Sheet 1: 所有接口详情
    # ═══════════════════════════════════════
    ws1 = wb.active
    ws1.title = "所有接口详情"

    # 元信息
    ws1.cell(row=1, column=1, value="API 响应时长测试报告").font = Font(name="微软雅黑", bold=True, size=14)
    ws1.merge_cells("A1:F1")
    for i, (k, v) in enumerate(zip(HEADER, META), 2):
        ws1.cell(row=i, column=1, value=k).font = Font(name="微软雅黑", bold=True, size=10)
        ws1.cell(row=i, column=2, value=v).font = cell_font
    start_row = 7

    headers = ["模块", "HTTP 方法", "路径", "状态码", "响应时长(ms)", "说明"]
    for c, h in enumerate(headers, 1):
        ws1.cell(row=start_row, column=c, value=h)
    style_header(ws1, start_row, 6)

    current_mod = None
    for i, (mod, method, path, status, ms, desc) in enumerate(ENDPOINTS, start_row + 1):
        ws1.cell(row=i, column=1, value=mod)
        ws1.cell(row=i, column=2, value=method)
        ws1.cell(row=i, column=3, value=path)
        ws1.cell(row=i, column=4, value=status)
        ws1.cell(row=i, column=5, value=ms)
        ws1.cell(row=i, column=6, value=desc)
        fill = green_fill if current_mod != mod else None
        current_mod = mod
        style_row(ws1, i, 6, fill)

    # 列宽
    ws1.column_dimensions["A"].width = 10
    ws1.column_dimensions["B"].width = 10
    ws1.column_dimensions["C"].width = 60
    ws1.column_dimensions["D"].width = 10
    ws1.column_dimensions["E"].width = 14
    ws1.column_dimensions["F"].width = 30

    # ═══════════════════════════════════════
    # Sheet 2: 模块汇总
    # ═══════════════════════════════════════
    ws2 = wb.create_sheet("模块汇总")
    ws2.cell(row=1, column=1, value="模块汇总统计").font = Font(name="微软雅黑", bold=True, size=14)
    ws2.merge_cells("A1:D1")

    headers2 = ["模块", "端点数", "平均响应时长(ms)", "成功率"]
    for c, h in enumerate(headers2, 1):
        ws2.cell(row=3, column=c, value=h)
    style_header(ws2, 3, 4)

    mod_order = ["认证", "聊天", "方案", "行程", "数据", "运维", "游记", "用户"]
    for i, mod in enumerate(mod_order, 4):
        info = MODULE_SUMMARY[mod]
        ws2.cell(row=i, column=1, value=mod)
        ws2.cell(row=i, column=2, value=info["count"])
        ws2.cell(row=i, column=3, value=info["avg"])
        ws2.cell(row=i, column=4, value=f"{info['count']}/{info['count']}")
        style_row(ws2, i, 4, green_fill if i % 2 == 0 else None)

    ws2.column_dimensions["A"].width = 12
    ws2.column_dimensions["B"].width = 10
    ws2.column_dimensions["C"].width = 20
    ws2.column_dimensions["D"].width = 10

    # ═══════════════════════════════════════
    # Sheet 3: 整体统计
    # ═══════════════════════════════════════
    ws3 = wb.create_sheet("整体统计")
    ws3.cell(row=1, column=1, value="整体统计").font = Font(name="微软雅黑", bold=True, size=14)
    ws3.merge_cells("A1:B1")

    stats = [
        ("总端点数", 59),
        ("成功 (2xx)", 59),
        ("失败 (非2xx)", 0),
        ("跳过/异常", 0),
        ("成功率", "100%"),
        ("平均响应时长", "642.1 ms"),
        ("中位响应时长", "371.8 ms"),
        ("最慢接口", "6276.7 ms"),
        ("最快接口", "0.1 ms"),
        ("最慢接口", "POST /travelogues — 生成游记（LLM 润色）"),
        ("最快接口", "PATCH /plans/{plan_id} — SSE Mock"),
    ]
    for c, h in enumerate(["指标", "值"], 1):
        ws3.cell(row=3, column=c, value=h)
    style_header(ws3, 3, 2)

    for i, (k, v) in enumerate(stats, 4):
        ws3.cell(row=i, column=1, value=k)
        ws3.cell(row=i, column=2, value=str(v))
        style_row(ws3, i, 2)
    ws3.column_dimensions["A"].width = 18
    ws3.column_dimensions["B"].width = 40

    # ── 冻结首行 ──
    ws1.freeze_panes = f"A{start_row + 1}"
    ws2.freeze_panes = "A4"
    ws3.freeze_panes = "A4"

    return wb


if __name__ == "__main__":
    wb = build_workbook()
    path = "docs/Sprint1/test/api_response_benchmark.xlsx"
    wb.save(path)
    print(f"Excel 报告已生成: {path}")
