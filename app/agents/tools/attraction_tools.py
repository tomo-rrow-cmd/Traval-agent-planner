"""
景点工具集
"""

ATTRACTION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_attractions",
            "description": "搜索指定城市的景点，可按分类和评分过滤",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称",
                    },
                    "category": {
                        "type": "string",
                        "description": "景点分类：自然风光 / 历史人文 / 主题公园 / 购物 / 其他",
                    },
                    "min_rating": {
                        "type": "number",
                        "description": "最低评分（0-5）",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "兴趣标签，如 ['亲子', '网红打卡', '免费']",
                    },
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_attraction_detail",
            "description": "获取单个景点的详细信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "attraction_name": {
                        "type": "string",
                        "description": "景点名称",
                    },
                },
                "required": ["attraction_name"],
            },
        },
    },
]
