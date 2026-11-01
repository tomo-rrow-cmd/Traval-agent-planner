"""美团 CLI 输出解析器 — Markdown → JSON"""

import html
import re


def clean_markdown_text(value: str) -> str:
    """将美团 Markdown 内联文本转换为可持久化的纯文本。"""
    text = html.unescape(str(value or ""))
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\((?:https?://|/)[^)]+\)", r"\1", text)
    text = re.sub(r"\\([\\`*_[\]{}()#+\-.!])", r"\1", text)
    text = re.sub(r"\*\*|__|`", "", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_hotels(markdown: str) -> list[dict]:
    hotels = []
    sections = re.split(r"\n##\s+", markdown)
    for section in sections:
        lines = section.strip().split("\n")
        h = _parse_block(lines)
        if h:
            hotels.append(h)
    return hotels


def _parse_block(lines: list) -> dict | None:
    h = {"name": "", "rating": 0.0, "price": 0, "price_note": "",
         "image": "", "link": "", "reason": "", "tags": []}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        m = re.search(r"!\[.*?\]\((https?://[^)]+)\)", line)
        if m:
            h["image"] = m.group(1); continue
        m = re.search(r"\[(?:\*\*)?(.+?)(?:\*\*)?\]\((https?://[^)]+)\)", line)
        if m:
            h["name"] = clean_markdown_text(m.group(1))
            h["link"] = m.group(2)
        m = re.search(r"美团真实评分\s*(\d+\.?\d*)", line)
        if m:
            h["rating"] = float(m.group(1))
        m = re.search(r"美团\s*(\S+型|\d+星级)", line)
        if m:
            h["tags"].append(f"美团{m.group(1)}")
        m = re.search(r"￥(\d+)\s*(起/晚|/晚|起)?", line)
        if m:
            h["price"] = int(m.group(1))
            h["price_note"] = m.group(2) or ""
        if h["name"] and not h["reason"] and len(line) > 30 and "http" not in line:
            clean = re.sub(r"\*\*|\[|\]|\(http[^)]+\)|!\[.*?\]\(.*?\)", "", line).strip()
            if clean and "￥" not in clean and "评分" not in clean:
                h["reason"] = clean_markdown_text(clean)
        for tag in ["近地铁", "新开业", "影音房", "停车", "叫醒服务", "洗衣",
                     "行李寄存", "智能客控", "商务出行", "拍照出片", "千兆网络",
                     "零压助眠房", "外宾适用", "即时确认", "预约发票", "严选好店"]:
            if tag in line and tag not in h["tags"]:
                h["tags"].append(tag)
    return h if h["name"] else None
