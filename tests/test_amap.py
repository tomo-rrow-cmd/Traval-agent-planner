"""测试高德地图路径规划参数。"""

import pytest

from app.services.map.amap import AmapService


@pytest.mark.asyncio
async def test_route_planning_only_adds_city_for_transit(monkeypatch):
    service = AmapService()
    requests = []

    async def fake_request(endpoint, params):
        requests.append((endpoint, dict(params)))
        return {"route": {"endpoint": endpoint}}

    monkeypatch.setattr(service, "_request", fake_request)

    await service.route_planning("1,2", "3,4", "transit", city="北京")
    await service.route_planning("1,2", "3,4", "walking", city="北京")
    await service.route_planning("1,2", "3,4", "driving", city="北京")

    assert requests[0][1]["city"] == "北京"
    assert "city" not in requests[1][1]
    assert "city" not in requests[2][1]
