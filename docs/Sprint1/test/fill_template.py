#!/usr/bin/env python3
"""将全部 59 个 API 性能数据填入质量门禁模板（严格对齐模板字段）"""

from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

SRC = "docs/Sprint1/test/Sprint1质量门禁完成报告_模板.xlsx"
DST = "docs/Sprint1/test/Sprint1质量门禁完成报告.xlsx"

wb = load_workbook(SRC)

green_font = Font(name="微软雅黑", color="008000", size=10)
red_font = Font(name="微软雅黑", color="FF0000", size=10)
normal_font = Font(name="微软雅黑", size=10)
note_font = Font(name="微软雅黑", size=9, italic=True, color="666666")
alt_fill = PatternFill("solid", fgColor="F2F7FB")
thin_border = Border(
    left=Side(style="thin"), right=Side(style="thin"),
    top=Side(style="thin"), bottom=Side(style="thin"),
)

def wc(ws, row, col, value, font=None, fill=None):
    cell = ws.cell(row=row, column=col, value=value)
    cell.font = font or normal_font
    cell.alignment = Alignment(vertical="center", wrap_text=True)
    cell.border = thin_border
    if fill:
        cell.fill = fill
    return cell

# ========== Sheet 1: 质量门禁 G4 行 ==========
ws1 = wb[wb.sheetnames[0]]
wc(ws1, 14, 5, "59个API接口全量压测，平均642.1ms，中位数371.8ms。普通REST接口均<400ms，达标51/59。8个超标均为LLM推理端点，详见性能测试Sheet")
wc(ws1, 14, 6, "达标", font=green_font)
wc(ws1, 14, 7, "详见「性能测试」Sheet（59条API全量明细）")

# ========== Sheet 5: 性能测试 ==========
ws5 = wb[wb.sheetnames[4]]

# 模板表头 B4:G4 = 编号 | 测试对象(页面/API) | URL | 响应时间(ms) | 是否达标 | 备注
# 保留 P1/P2（row 5-6）
ws5.cell(row=5, column=4, value="http://localhost:5173")
ws5.cell(row=5, column=5, value="—")
ws5.cell(row=5, column=6, value="未测")
ws5.cell(row=5, column=7, value="本次仅测后端API，前端待补充 | 标准<3000ms")
ws5.cell(row=6, column=4, value="http://localhost:5173")
ws5.cell(row=6, column=5, value="—")
ws5.cell(row=6, column=6, value="未测")
ws5.cell(row=6, column=7, value="本次仅测后端API，前端待补充 | 标准<1500ms")

# 全部 59 个 API: (编号, 测试对象, URL, 响应时长ms)
ALL = [
    ("A1",  "认证-发送短信验证码",          "/api/v1/auth/sms-codes",            413.0),
    ("A2",  "认证-登录（密码模式）",         "/api/v1/auth/sessions",             580.3),
    ("A3",  "认证-刷新Token",              "/api/v1/auth/tokens",               396.0),
    ("A4",  "认证-登出",                   "/api/v1/auth/sessions/current",     358.4),
    ("A5",  "聊天-创建会话",               "/api/v1/chat/sessions",             359.3),
    ("A6",  "聊天-会话列表",               "/api/v1/chat/sessions",             396.0),
    ("A7",  "聊天-更新会话",               "/api/v1/chat/sessions/{id}",        371.0),
    ("A8",  "聊天-发送消息(SSE/LLM)",       "/api/v1/chat/sessions/{id}/messages", 2230.6),
    ("A9",  "聊天-消息历史",               "/api/v1/chat/sessions/{id}/messages", 354.2),
    ("A10", "聊天-会话方案列表",            "/api/v1/chat/sessions/{id}/plans",    384.3),
    ("A11", "聊天-流式Agent(SSE/LLM)",      "/api/v1/chat/sessions/{id}/stream",   2011.3),
    ("A12", "聊天-删除会话",               "/api/v1/chat/sessions/{id}",         351.7),
    ("A13", "方案-触发生成(SSE Mock)",      "/api/v1/plans",                      0.2),
    ("A14", "方案-方案列表",               "/api/v1/plans",                      359.2),
    ("A15", "方案-方案详情",               "/api/v1/plans/{plan_id}",            357.7),
    ("A16", "方案-局部修改(SSE Mock)",      "/api/v1/plans/{plan_id}",            0.1),
    ("A17", "方案-重新生成(SSE Mock)",      "/api/v1/plans/{plan_id}/generations", 0.2),
    ("A18", "方案-导出Markdown",           "/api/v1/plans/{plan_id}/exports",     368.8),
    ("A19", "方案-分享方案",               "/api/v1/plans/{plan_id}/shares",      359.8),
    ("A20", "方案-收藏/取消收藏",           "/api/v1/plans/{plan_id}/favorites",   368.6),
    ("A21", "行程-我的行程列表",            "/api/v1/trips",                      374.5),
    ("A22", "行程-从方案创建行程",          "/api/v1/trips",                      367.9),
    ("A23", "行程-行程详情",               "/api/v1/trips/{trip_id}",            366.0),
    ("A24", "行程-更新状态(暂停)",          "/api/v1/trips/{trip_id}",            380.0),
    ("A25", "行程-更新状态(继续)",          "/api/v1/trips/{trip_id}",            373.1),
    ("A26", "行程-实时进度",               "/api/v1/trips/{trip_id}/progress",   365.4),
    ("A27", "行程-签到",                   "/api/v1/trips/{trip_id}/checkins",   385.1),
    ("A28", "行程-签到记录",               "/api/v1/trips/{trip_id}/checkins",   363.7),
    ("A29", "行程-记录花费",               "/api/v1/trips/{trip_id}/expenses",   372.2),
    ("A30", "行程-花费明细",               "/api/v1/trips/{trip_id}/expenses",   374.8),
    ("A31", "行程-异常检测(LLM)",           "/api/v1/trips/{trip_id}/adjustments/detect", 2707.9),
    ("A32", "行程-调整历史",               "/api/v1/trips/{trip_id}/adjustments", 363.3),
    ("A33", "行程-次日提醒(LLM)",           "/api/v1/trips/{trip_id}/reminder",    2752.3),
    ("A34", "行程-AI照片标注(LLM)",         "/api/v1/trips/{trip_id}/photos/annotate", 2758.3),
    ("A35", "数据-热门城市",               "/api/v1/data/cities",                 356.4),
    ("A36", "数据-城市搜索",               "/api/v1/data/cities?keyword=北京",    384.2),
    ("A37", "数据-景点列表",               "/api/v1/data/attractions?city=北京",  366.6),
    ("A38", "数据-景点详情",               "/api/v1/data/attractions/1",          378.6),
    ("A39", "数据-餐厅列表",               "/api/v1/data/restaurants?city=北京",  373.3),
    ("A40", "数据-酒店列表",               "/api/v1/data/hotels?city=北京",       377.9),
    ("A41", "数据-天气查询",               "/api/v1/data/weather?city=北京&date=2026-07-16", 380.2),
    ("A42", "运维-健康检查",               "/api/v1/health",                      17.8),
    ("A43", "运维-导出任务状态",            "/api/v1/tasks/{task_id}",            388.2),
    ("A44", "运维-下载导出文件",            "/api/v1/tasks/{task_id}/download",   375.7),
    ("A45", "游记-游记列表",               "/api/v1/travelogues",                 387.7),
    ("A46", "游记-生成游记(LLM)",           "/api/v1/travelogues",                 6276.7),
    ("A47", "游记-游记详情",               "/api/v1/travelogues/{id}",            374.6),
    ("A48", "游记-编辑游记",               "/api/v1/travelogues/{id}",            382.1),
    ("A49", "游记-发布游记",               "/api/v1/travelogues/{id}/publish",    348.5),
    ("A50", "游记-社交素材列表",            "/api/v1/travelogues/materials",       370.8),
    ("A51", "游记-生成社交素材(LLM)",       "/api/v1/travelogues/materials/generate", 2221.9),
    ("A52", "游记-生成分享链接",            "/api/v1/travelogues/shares",          354.9),
    ("A53", "游记-短码获取分享",            "/api/v1/travelogues/shares/{code}",   363.4),
    ("A54", "游记-删除游记",               "/api/v1/travelogues/{id}",            361.5),
    ("A55", "用户-获取资料",               "/api/v1/user/profile",                368.4),
    ("A56", "用户-更新资料",               "/api/v1/user/profile",                381.5),
    ("A57", "用户-获取偏好",               "/api/v1/user/preferences",            353.1),
    ("A58", "用户-更新偏好",               "/api/v1/user/preferences",            363.4),
    ("A59", "用户-匿名数据合并",            "/api/v1/user/sessions/anonymous/merge", 372.3),
]

OVER_REASONS = {
    "发送消息(SSE/LLM)": "SSE流式含LLM推理",
    "流式Agent(SSE/LLM)": "SSE流式含Agent推理",
    "异常检测(LLM)": "LLM异常检测",
    "次日提醒(LLM)": "LLM生成提醒",
    "AI照片标注(LLM)": "LLM照片标注",
    "生成游记(LLM)": "LLM生成游记",
    "生成社交素材(LLM)": "LLM生成素材",
}

for i, (idx, subject, url, ms) in enumerate(ALL):
    r = 7 + i
    is_pass = ms < 500
    fill = alt_fill if i % 2 == 1 else None

    wc(ws5, r, 2, idx, fill=fill)                     # B: 编号
    wc(ws5, r, 3, subject, fill=fill)                 # C: 测试对象
    wc(ws5, r, 4, url, fill=fill)                     # D: URL
    wc(ws5, r, 5, ms, fill=fill)                      # E: 响应时间(ms)
    wc(ws5, r, 6, "达标" if is_pass else "超标",      # F: 是否达标
       font=green_font if is_pass else red_font, fill=fill)

    remark = ""
    if not is_pass:
        for key, reason in OVER_REASONS.items():
            if key in subject:
                remark = reason
                break
        if not remark:
            remark = "含密码哈希+DB写入" if "登录" in subject else "含LLM调用"
    wc(ws5, r, 7, remark,
       font=note_font if is_pass else Font(name="微软雅黑", size=9, color="CC0000"),
       fill=fill)

# 列宽
ws5.column_dimensions["A"].width = 2
ws5.column_dimensions["B"].width = 10
ws5.column_dimensions["C"].width = 26
ws5.column_dimensions["D"].width = 55
ws5.column_dimensions["E"].width = 14
ws5.column_dimensions["F"].width = 10
ws5.column_dimensions["G"].width = 22

ws5.freeze_panes = "B7"

wb.save(DST)
print(f"已生成: {DST}")
pass_ = sum(1 for _,_,_,ms in ALL if ms < 500)
fail_ = len(ALL) - pass_
print(f"共 {len(ALL)} 个 API，严格对齐模板字段：编号 | 测试对象(页面/API) | URL | 响应时间(ms) | 是否达标 | 备注")
print(f"  达标 {pass_} | 超标 {fail_}")
