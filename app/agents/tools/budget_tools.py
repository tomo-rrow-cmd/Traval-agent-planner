"""
预算工具集
"""

BUDGET_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculate_budget",
            "description": "计算旅行总预算及各分类明细",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "旅行天数",
                    },
                    "travelers": {
                        "type": "integer",
                        "description": "出行人数",
                    },
                    "attractions_cost": {
                        "type": "number",
                        "description": "景点门票总费用",
                    },
                    "hotels_cost": {
                        "type": "number",
                        "description": "住宿总费用",
                    },
                    "meals_cost": {
                        "type": "number",
                        "description": "餐饮总费用",
                    },
                    "transport_cost": {
                        "type": "number",
                        "description": "交通总费用",
                    },
                },
                "required": ["days", "travelers"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_budget_allocation",
            "description": "根据总预算给出各分类的合理分配建议",
            "parameters": {
                "type": "object",
                "properties": {
                    "total_budget": {
                        "type": "number",
                        "description": "总预算（元）",
                    },
                    "days": {
                        "type": "integer",
                        "description": "旅行天数",
                    },
                    "travelers": {
                        "type": "integer",
                        "description": "出行人数",
                    },
                    "destination": {
                        "type": "string",
                        "description": "目的地（不同城市消费水平不同）",
                    },
                },
                "required": ["total_budget", "days", "destination"],
            },
        },
    },
]
