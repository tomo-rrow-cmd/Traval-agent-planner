"""
地图工具集 - Agent 可调用的地图相关 Function Calling 工具定义
"""

MAP_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_poi",
            "description": "搜索指定城市的 POI（景点、餐厅、酒店等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "string",
                        "description": "搜索关键词，如 '故宫'、'火锅'",
                    },
                    "city": {
                        "type": "string",
                        "description": "城市名称，如 '北京'",
                    },
                    "types": {
                        "type": "string",
                        "description": "POI 类型：scenic（景点）/ dining（餐饮）/ hotel（酒店）",
                        "enum": ["scenic", "dining", "hotel"],
                    },
                },
                "required": ["keywords", "city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_route",
            "description": "获取两点之间的路线规划",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {
                        "type": "string",
                        "description": "起点坐标，格式 'lng,lat'",
                    },
                    "destination": {
                        "type": "string",
                        "description": "终点坐标，格式 'lng,lat'",
                    },
                    "mode": {
                        "type": "string",
                        "description": "出行方式",
                        "enum": ["driving", "walking", "transit"],
                    },
                },
                "required": ["origin", "destination"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "geocode",
            "description": "将地址转换为经纬度",
            "parameters": {
                "type": "object",
                "properties": {
                    "address": {
                        "type": "string",
                        "description": "详细地址",
                    },
                    "city": {
                        "type": "string",
                        "description": "所在城市",
                    },
                },
                "required": ["address"],
            },
        },
    },
]
