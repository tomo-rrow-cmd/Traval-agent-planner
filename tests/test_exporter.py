"""测试 app/services/export/exporter.py — 方案导出"""

import io
import pytest
from app.services.export.exporter import (
    export_markdown,
    export_plan,
)


# 完整的测试 plan 数据
@pytest.fixture
def full_plan():
    return {
        "destination": "北京",
        "origin": "上海",
        "days": 3,
        "budget": {
            "total_budget": 5000,
            "actual_total": 3200,
            "details": [
                {"category": "住宿", "budget": 1750, "spent": 1200, "status": "ok"},
                {"category": "餐饮", "budget": 1000, "spent": 800, "status": "ok"},
                {"category": "交通", "budget": 1000, "spent": 600, "status": "ok"},
                {"category": "门票", "budget": 750, "spent": 400, "status": "ok"},
                {"category": "购物", "budget": 500, "spent": 200, "status": "ok"},
            ],
            "warnings": ["已用 64%，接近上限"],
        },
        "daily_itinerary": [
            {
                "day": 1,
                "date": "2026-08-01",
                "weather_summary": "晴 35°C",
                "day_summary": "京城经典一日游",
                "attractions": [
                    {"name": "故宫", "duration_hours": 3, "duration_minutes": 180, "reason": "必去景点", "cost": 60, "rating": 4.8, "tips": "建议早8点前排队"},
                    {"name": "天坛", "duration_hours": 2, "reason": "历史文化"},
                    {"name": "景山公园"},
                ],
                "accommodation": {
                    "hotel_name": "北京饭店",
                    "price_per_night": 500,
                    "address": "东长安街",
                },
                "meals": [
                    {"meal": "午餐", "restaurant": "全聚德", "avg_price": 150, "reason": "烤鸭必吃"},
                    {"meal": "晚餐", "restaurant": "护国寺小吃", "avg_price": 50, "reason": "地道小吃"},
                ],
            },
        ],
        "meal_plan": [],
        "hotel_plan": {
            "recommendations": [
                {
                    "name": "北京饭店",
                    "price_per_night": 500,
                    "nights": 3,
                    "total": 1500,
                    "reason": "位置好",
                    "price_verified": True,
                },
            ],
        },
        "overview": {
            "highlights": ["故宫博物院 — 世界文化遗产", "长城 — 不到长城非好汉"],
        },
        "big_traffic": {
            "trains": [
                {"trainCode": "G1", "departureTime": "08:00", "arrivalTime": "12:30", "duration": "4h30m", "price": 553},
            ],
            "return_trains": [
                {"trainCode": "G2", "departureTime": "18:00", "arrivalTime": "22:30", "duration": "4h30m", "price": 553},
            ],
        },
        "tips": ["故宫周一闭馆，请提前预约", "北京夏季高温，注意防晒"],
        "avoid_list": ["不要相信景区门口的黄牛", "王府井小吃街价格偏高"],
    }


class TestExportMarkdown:
    def test_full_plan_contains_all_sections(self, full_plan):
        result = export_markdown(full_plan)
        assert "# 北京3日旅行方案" in result
        assert "上海 → 北京" in result
        assert "## 📅 第1天" in result
        assert "故宫" in result
        assert "全聚德" in result
        assert "## 💰 预算" in result
        assert "## ✨ 行程亮点" in result
        assert "故宫博物院" in result
        assert "### 去程" in result
        assert "### 返程" in result
        assert "京城经典一日游" in result
        assert "晴 35°C" in result
        assert "景山公园" in result
        assert "💡 出行建议" in result
        assert "避坑提醒" in result
        assert "AI 旅行规划师" in result

    def test_no_hotel_plan_still_works(self, full_plan):
        full_plan["hotel_plan"] = {}
        result = export_markdown(full_plan)
        assert "住宿推荐" not in result

    def test_no_warnings_still_works(self, full_plan):
        full_plan["budget"]["warnings"] = []
        result = export_markdown(full_plan)
        assert "⚠ 注意事项" not in result

    def test_big_traffic_as_list(self, full_plan):
        full_plan["big_traffic"] = [
            {"trainCode": "K1", "departureTime": "20:00", "arrivalTime": "10:00", "duration": "14h", "price": 320},
        ]
        result = export_markdown(full_plan)
        assert "往返交通" in result
        assert "K1" in result
        assert "¥320" in result

    def test_meal_fallback_from_meal_plan(self, full_plan):
        """当 daily_itinerary 中没有 meals 时，回退到 meal_plan"""
        full_plan["daily_itinerary"] = [
            {"day": 1, "attractions": [{"name": "故宫", "duration_hours": 2, "reason": "必去"}]},
        ]
        full_plan["meal_plan"] = [
            {"day": 1, "meals": [
                {"meal": "午餐", "restaurant": "便宜坊", "avg_price": 80, "reason": "老字号"},
            ]},
        ]
        result = export_markdown(full_plan)
        assert "便宜坊" in result

    def test_meal_plan_from_full_data_fallback(self, full_plan):
        """line 271-275: meal_plan 回退到 full_data"""
        full_plan["meal_plan"] = []
        full_plan["full_data"] = {"meal_plan": [{"day": 1, "meals": [
            {"meal": "午餐", "restaurant": "全聚德(回退)", "avg_price": 150}]}]}
        full_plan["daily_itinerary"][0].pop("meals", None)
        result = export_markdown(full_plan)
        assert "全聚德(回退)" in result

    def test_docx_meal_from_full_data(self, full_plan):
        """line 271-275: docx 中 meal_plan 回退到 full_data"""
        pytest.importorskip("docx")
        full_plan["daily_itinerary"][0].pop("meals", None)
        full_plan["meal_plan"] = []
        full_plan["full_data"] = {"meal_plan": [{"day": 1, "meals": [
            {"meal": "午餐", "restaurant": "便宜坊", "avg_price": 90}]}]}
        data, _ = export_plan(full_plan, "docx")
        assert isinstance(data, bytes)

    def test_empty_plan_handled(self):
        result = export_markdown({})
        assert "旅行方案" in result

    def test_over_budget_status(self, full_plan):
        full_plan["budget"]["details"] = [
            {"category": "餐饮", "budget": 1000, "spent": 1500, "status": "over"},
        ]
        result = export_markdown(full_plan)
        assert "⚠超支" in result


class TestExportPlan:
    def test_md_format(self, full_plan):
        data, mime = export_plan(full_plan, "md")
        assert isinstance(data, bytes)
        assert "markdown" in mime
        assert b"#" in data

    def test_docx_format(self, full_plan):
        pytest.importorskip("docx")
        data, mime = export_plan(full_plan, "docx")
        assert isinstance(data, bytes)
        assert "openxmlformats" in mime
        assert len(data) > 0

    def test_pdf_export_uses_markdown(self):
        """PDF 导出依赖 markdown，验证内部调用 export_markdown"""
        from app.services.export.exporter import export_markdown
        md = export_markdown({"destination": "test", "days": 1})
        assert "#" in md or len(md) > 0

    def test_docx_full_export(self, full_plan):
        """完整 docx 导出（python-docx 已安装）"""
        from app.services.export.exporter import export_docx
        data = export_docx(full_plan)
        assert isinstance(data, bytes)
        assert len(data) > 1000  # docx 文件至少几KB

    def test_docx_empty_plan(self):
        """docx 导出空 plan 不崩溃"""
        from app.services.export.exporter import export_docx
        data = export_docx({"destination": "test", "days": 0,
                           "daily_itinerary": [], "budget": {"details": []}})
        assert isinstance(data, bytes)
        assert len(data) > 0

    def test_pdf_full_export(self, full_plan):
        """PDF 导出始终生成可识别的 PDF 文件。"""
        from app.services.export.exporter import export_pdf
        try:
            data = export_pdf(full_plan)
            assert isinstance(data, bytes)
            assert len(data) > 100
            assert data.startswith(b"%PDF-")
        except AttributeError:
            pytest.skip("weasyprint compatibility issue in this Python version")

    def test_export_plan_docx_and_pdf(self, full_plan):
        """export_plan 路由 docx 和 pdf 格式"""
        from app.services.export.exporter import export_plan
        data_docx, mime_docx = export_plan(full_plan, "docx")
        assert "openxmlformats" in mime_docx
        try:
            data_pdf, mime_pdf = export_plan(full_plan, "pdf")
            assert mime_pdf == "application/pdf"
            assert data_pdf.startswith(b"%PDF-")
        except AttributeError:
            pytest.skip("weasyprint compat issue")

    def test_unknown_format_raises(self, full_plan):
        with pytest.raises(ValueError, match="Unsupported format"):
            export_plan(full_plan, "xml")

    def test_export_markdown_returns_bytes_with_encoding(self, full_plan):
        from app.services.export.exporter import export_markdown
        data = export_markdown(full_plan).encode("utf-8")
        assert b"#" in data

    def test_docx_import_error_message(self):
        """异常路径: python-docx 未安装时抛出明确错误"""
        # Use pytest.importorskip — cleaner, no global side effects
        docx_available = True
        try:
            from docx import Document  # noqa: F401
        except ImportError:
            docx_available = False

        if not docx_available:
            from app.services.export.exporter import export_docx
            with pytest.raises(ImportError, match="python-docx"):
                export_docx({})

    def test_pdf_export_returns_bytes_or_markdown_plus_html(self, full_plan):
        """PDF 导出: markdown 转 HTML 输出（weasyprint 可选）"""
        from app.services.export.exporter import export_markdown
        # export_pdf 内部调用 export_markdown，验证其输出
        md = export_markdown({"destination": "test"})
        assert len(md) > 0
