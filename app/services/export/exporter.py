"""
方案文件导出 — MD / DOCX / PDF

输入：PlanResponse.model_dump() 字典（含 full_data 回退字段）
输出：文件二进制数据
"""

import io
from pathlib import Path
import re
from typing import Any


def _get_activities(day: dict) -> list:
    """兼容 daily_itinerary 中 activities / attractions 两种字段名"""
    return day.get("activities") or day.get("attractions") or []


def _get_origin(plan: dict) -> str:
    """兼容 origin / departure 两种字段名"""
    return plan.get("departure") or plan.get("origin") or ""


def _get_budget(plan: dict) -> dict:
    """从 plan 中提取预算数据"""
    b = plan.get("budget") or plan.get("budget_detail") or {}
    # 如果 budget 为空但 full_data 中有，则从 full_data 取
    if not b.get("details") and plan.get("full_data"):
        b = plan["full_data"].get("budget") or b
    return b


def export_markdown(plan: dict) -> str:
    """方案 → Markdown 字符串"""
    dest = plan.get("destination", "")
    origin = _get_origin(plan)
    days = plan.get("days", 0)
    budget = _get_budget(plan)

    title = plan.get("title") or f"{dest}{days}日旅行方案" or "旅行方案"
    lines = [
        f"# {title}",
        "",
    ]
    if origin and dest:
        lines.append(f"> **{origin} → {dest}** | {days}天")
    elif dest:
        lines.append(f"> **{dest}** | {days}天")
    lines.append("")

    # 行程亮点
    overview = plan.get("overview") or {}
    highlights = overview.get("highlights") or plan.get("full_data", {}).get("overview", {}).get("highlights", [])
    if highlights:
        lines.append("## ✨ 行程亮点")
        for h in highlights:
            lines.append(f"- {h}")
        lines.append("")

    # 交通信息
    big_traffic = plan.get("big_traffic")
    if big_traffic:
        if isinstance(big_traffic, list):
            lines.append("## 🚄 往返交通")
            for t in big_traffic:
                code = t.get("trainCode", "")
                dep = t.get("departureTime", "")
                arr = t.get("arrivalTime", "")
                dur = t.get("duration", "")
                price = t.get("price")
                line = f"- **{code}**"
                if dep and arr:
                    line += f" {dep} → {arr}"
                if dur:
                    line += f" ({dur})"
                if price is not None:
                    line += f" ¥{price}"
                lines.append(line)
            lines.append("")
        elif isinstance(big_traffic, dict):
            trains = big_traffic.get("trains", [])
            return_trains = big_traffic.get("return_trains", [])
            if trains:
                lines.append("### 去程")
                for t in trains:
                    code = t.get("trainCode", "")
                    dep = t.get("departureTime", "")
                    arr = t.get("arrivalTime", "")
                    dur = t.get("duration", "")
                    price = t.get("price")
                    line = f"- **{code}**"
                    if dep and arr:
                        line += f" {dep} → {arr}"
                    if dur:
                        line += f" ({dur})"
                    if price is not None:
                        line += f" ¥{price}"
                    lines.append(line)
                lines.append("")
            if return_trains:
                lines.append("### 返程")
                for t in return_trains:
                    code = t.get("trainCode", "")
                    dep = t.get("departureTime", "")
                    arr = t.get("arrivalTime", "")
                    dur = t.get("duration", "")
                    price = t.get("price")
                    line = f"- **{code}**"
                    if dep and arr:
                        line += f" {dep} → {arr}"
                    if dur:
                        line += f" ({dur})"
                    if price is not None:
                        line += f" ¥{price}"
                    lines.append(line)
                lines.append("")

    # 每日行程
    for day in plan.get("daily_itinerary", []):
        d = day.get("day", "?")
        date_str = day.get("date", "")
        weather = day.get("weather_summary", "")
        date_part = f"（{date_str}）" if date_str else ""
        weather_part = f" {weather}" if weather else ""
        lines.append(f"## 📅 第{d}天{date_part}{weather_part}")
        if day.get("day_summary"):
            lines.append(f"> {day['day_summary']}")
        lines.append("")

        acts = _get_activities(day)
        if acts:
            lines.append("### 景点与活动")
            for a in acts:
                name = a.get("title") or a.get("name") or "未知"
                desc = a.get("description") or a.get("reason") or ""
                if desc:
                    lines.append(f"- **{name}** — {desc}")
                else:
                    lines.append(f"- **{name}**")
                tags = a.get("tags") or []
                if a.get("duration_minutes"):
                    mins = a["duration_minutes"]
                    tags.append(f"⏱ {mins // 60}h{mins % 60}min")
                if a.get("cost") is not None:
                    cost = a["cost"]
                    tags.append("免费" if cost == 0 else f"¥{cost}")
                if a.get("rating"):
                    tags.append(f"⭐ {a['rating']}")
                if tags:
                    lines.append(f"  {' | '.join(tags)}")
                if a.get("tips"):
                    tips = a["tips"] if isinstance(a["tips"], str) else "; ".join(a["tips"])
                    lines.append(f"  💡 {tips}")
                lines.append("")

        # 餐饮
        meals = day.get("meals", [])
        if not meals:
            meal_plan = plan.get("meal_plan") or plan.get("full_data", {}).get("meal_plan", [])
            for mp in meal_plan:
                if mp.get("day") == d:
                    meals = mp.get("meals", [])
                    break
        if meals:
            lines.append("### 🍽 餐饮")
            for m in meals:
                line = f"- **{m.get('restaurant') or m.get('meal','餐')}**"
                if m.get("avg_price") or m.get("cost"):
                    line += f" ¥{m.get('avg_price') or m.get('cost'):.0f}"
                if m.get("reason") or m.get("description"):
                    line += f" — {m.get('reason') or m.get('description')}"
                lines.append(line)
            lines.append("")

        # 住宿
        accommodation = day.get("accommodation") or day.get("hotel") or {}
        if accommodation:
            name = accommodation.get("hotel_name") or accommodation.get("name") or "住宿"
            line = f"🏨 **{name}**"
            if accommodation.get("price") or accommodation.get("price_per_night"):
                line += f" ¥{accommodation.get('price') or accommodation.get('price_per_night'):.0f}/晚"
            if accommodation.get("address"):
                line += f"（{accommodation['address']}）"
            lines.append(line)
            lines.append("")

    # 预算
    lines.append("## 💰 预算")
    total_budget = plan.get("total_budget", 0) or budget.get("total_budget", 0)
    estimated_cost = plan.get("estimated_cost", 0) or budget.get("actual_total", 0)
    if total_budget:
        lines.append(f"总预算：¥{total_budget:.0f}")
    if estimated_cost:
        lines.append(f"预估花费：¥{estimated_cost:.0f}")
    details = budget.get("details", [])
    if details:
        lines.append("")
        lines.append("| 分类 | 预算 | 花费 | 状态 |")
        lines.append("|------|------|------|------|")
        for d in details:
            cat = d.get("category", "其他")
            bgt = d.get("budget", 0)
            spent = d.get("spent", 0)
            status = "⚠超支" if d.get("status") == "over" else "✅"
            lines.append(f"| {cat} | ¥{bgt:.0f} | ¥{spent:.0f} | {status} |")
        lines.append(f"| **合计** | **¥{total_budget:.0f}** | **¥{estimated_cost:.0f}** | |")
    lines.append("")

    # 出行建议
    tips = plan.get("tips") or plan.get("full_data", {}).get("tips", [])
    if tips:
        lines.append("## 💡 出行建议")
        for t in tips:
            lines.append(f"- {t}")
        lines.append("")

    # 避坑提醒
    avoid = plan.get("avoid_list") or plan.get("full_data", {}).get("avoid_list", [])
    if avoid:
        lines.append("## ⚠️ 避坑提醒")
        for a in avoid:
            lines.append(f"- {a}")
        lines.append("")

    lines.append("---")
    lines.append("*AI 旅行规划师自动生成*")
    return "\n".join(lines)


def export_docx(plan: dict) -> bytes:
    """方案 → .docx 文件"""
    try:
        from docx import Document
        from docx.shared import Pt, Inches
    except ImportError:
        raise ImportError("python-docx not installed. Run: pip install python-docx")

    doc = Document()
    style = doc.styles["Normal"]
    style.font.size = Pt(11)

    dest = plan.get("destination", "")
    days = plan.get("days", 0)
    title = plan.get("title") or f"{dest}{days}日旅行方案" or "旅行方案"
    doc.add_heading(title, 0)

    origin = _get_origin(plan)
    budget = _get_budget(plan)
    total_budget = plan.get("total_budget", 0) or budget.get("total_budget", 0)
    estimated_cost = plan.get("estimated_cost", 0) or budget.get("actual_total", 0)
    doc.add_paragraph(
        f"{' → '.join(filter(None, [origin, dest]))} | "
        f"总预算 ¥{total_budget:.0f} | "
        f"预估花费 ¥{estimated_cost:.0f}"
    )

    for day in plan.get("daily_itinerary", []):
        d = day.get("day", "?")
        doc.add_heading(f"第 {d} 天", 1)

        acts = _get_activities(day)
        if acts:
            doc.add_heading("景点与活动", 2)
            for a in acts:
                name = a.get("title") or a.get("name") or "未知"
                desc = a.get("description") or a.get("reason") or ""
                doc.add_paragraph(name, style="List Bullet")
                if desc:
                    doc.add_paragraph(desc)

        meals = day.get("meals", [])
        if not meals:
            meal_plan = plan.get("meal_plan") or plan.get("full_data", {}).get("meal_plan", [])
            for mp in meal_plan:
                if mp.get("day") == d:
                    meals = mp.get("meals", [])
                    break
        if meals:
            doc.add_heading("餐饮", 2)
            for m in meals:
                doc.add_paragraph(
                    f"{m.get('restaurant') or m.get('meal','餐')} ¥{m.get('avg_price') or m.get('cost',0):.0f}",
                    style="List Bullet",
                )

        accommodation = day.get("accommodation") or day.get("hotel") or {}
        if accommodation.get("hotel_name") or accommodation.get("name"):
            name = accommodation.get("hotel_name") or accommodation.get("name", "住宿")
            price = accommodation.get("price") or accommodation.get("price_per_night", 0)
            addr = accommodation.get("address", "")
            text = f"{name} ¥{price:.0f}/晚"
            if addr:
                text += f"（{addr}）"
            doc.add_paragraph(text)

    doc.add_heading("预算明细", 1)
    table = doc.add_table(rows=1, cols=4)
    for i, text in enumerate(["类别", "预算", "花费", "状态"]):
        table.rows[0].cells[i].text = text
    for d in budget.get("details", []):
        row = table.add_row()
        row.cells[0].text = d.get("category", "其他")
        row.cells[1].text = f"¥{d.get('budget', 0):.0f}"
        row.cells[2].text = f"¥{d.get('spent', 0):.0f}"
        row.cells[3].text = "⚠" if d.get("status") == "over" else "✓"

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def export_pdf(plan: dict) -> bytes:
    """方案 → 真正的 PDF；WeasyPrint 不可用时降级到纯 Python fpdf2。"""
    import markdown as _md

    md_text = export_markdown(plan)

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
body {{ font-family: 'Microsoft YaHei', sans-serif; max-width: 800px; margin: auto; padding: 20px; }}
h1 {{ color: #333; }} h2 {{ color: #555; border-bottom: 1px solid #ddd; }}
table {{ border-collapse: collapse; width: 100%; }}
td, th {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    </style></head>
<body>{_md.markdown(md_text)}</body></html>"""

    try:
        import pydyf

        compatibility_methods = {
            "transform": "set_matrix",
            "text_matrix": "set_text_matrix",
        }
        for legacy_name, current_name in compatibility_methods.items():
            if not hasattr(pydyf.Stream, legacy_name):
                setattr(pydyf.Stream, legacy_name, getattr(pydyf.Stream, current_name))

        from weasyprint import HTML
        content = HTML(string=html).write_pdf()
        if content.startswith(b"%PDF-"):
            return content
    except Exception:
        pass

    try:
        from fpdf import FPDF

        font_path = Path(__file__).parent / "fonts" / "NotoSansSC-Regular.ttf"
        if not font_path.exists():
            raise RuntimeError("PDF 中文字体文件缺失")

        pdf = FPDF()
        pdf.add_page()
        pdf.add_font("NotoSansSC", "", str(font_path))
        for line in md_text.splitlines():
            text = re.sub(r"\*+", "", line).strip()
            if not text:
                pdf.ln(2)
                continue
            size = 18 if line.startswith("# ") else 14 if line.startswith("## ") else 10
            pdf.set_font("NotoSansSC", size=size)
            try:
                pdf.multi_cell(0, 7 if size > 10 else 6, text.lstrip("#- "))
            except Exception:
                continue
        content = bytes(pdf.output())
        if not content.startswith(b"%PDF-"):
            raise RuntimeError("PDF 渲染结果格式无效")
        return content
    except Exception as exc:
        raise RuntimeError("PDF 生成失败") from exc


def export_plan(plan: dict, fmt: str = "md") -> tuple[bytes, str]:
    """
    统一导出入口。

    Returns: (file_bytes, mime_type)
    """
    if fmt == "md":
        return export_markdown(plan).encode("utf-8"), "text/markdown; charset=utf-8"
    elif fmt == "docx":
        return export_docx(plan), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif fmt == "pdf":
        content = export_pdf(plan)
        return content, "application/pdf"
    else:
        raise ValueError(f"Unsupported format: {fmt}")
