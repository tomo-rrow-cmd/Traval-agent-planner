"""TravelogueService 的业务分支与权限测试。"""

import socket
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.common import PaginatedData
from app.services.application.travelogue_service import TravelogueService


@pytest.fixture(autouse=True)
def block_external_network(monkeypatch):
    def fail_external_connection(*_args, **_kwargs):
        raise AssertionError("unit tests must not access external services or databases")

    monkeypatch.setattr(socket.socket, "connect", fail_external_connection)
    monkeypatch.setattr(socket, "create_connection", fail_external_connection)


def _travelogue(**overrides):
    values = {
        "id": "travelogue-1",
        "trip_id": "trip-1",
        "user_id": "user-1",
        "title": "北京三日",
        "content": "游记正文",
        "cover_url": None,
        "style": None,
        "photos": None,
        "total_days": 3,
        "total_pois": 8,
        "total_cost": 1200,
        "total_photos": 5,
        "status": "draft",
        "created_at": datetime(2026, 7, 17, 10, 0),
        "updated_at": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _material(**overrides):
    values = {
        "id": "material-1",
        "trip_id": "trip-1",
        "user_id": "user-1",
        "type": "xiaohongshu",
        "title": "故宫打卡",
        "content": "素材正文",
        "hashtags": None,
        "location_tag": "北京",
        "images": None,
        "layout": "grid",
        "overlay_data": {},
        "source_day": 1,
        "source_poi": "故宫",
        "is_generated": True,
        "is_favorite": False,
        "used_in_travelogue": False,
        "created_at": datetime(2026, 7, 17, 11, 0),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _share(**overrides):
    values = {
        "id": "share-1",
        "user_id": "user-1",
        "target_type": "travelogue",
        "target_id": "travelogue-1",
        "share_code": "abc123",
        "password": None,
        "expire_at": None,
        "view_count": 0,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.fixture
def travelogue_repo():
    return MagicMock(
        create_for_trip=AsyncMock(),
        get_by_id=AsyncMock(return_value=None),
        get_by_trip=AsyncMock(return_value=None),
        list_by_user=AsyncMock(return_value=[]),
        count_by_user=AsyncMock(return_value=0),
        update=AsyncMock(),
        delete_by_id=AsyncMock(return_value=True),
    )


@pytest.fixture
def material_repo():
    return MagicMock(
        create_material=AsyncMock(),
        list_by_trip=AsyncMock(return_value=[]),
        get_by_id=AsyncMock(return_value=None),
        update=AsyncMock(),
    )


@pytest.fixture
def share_repo():
    return MagicMock(
        create_share=AsyncMock(),
        get_by_code=AsyncMock(return_value=None),
        update=AsyncMock(),
    )


@pytest.fixture
def service(travelogue_repo, material_repo, share_repo):
    return TravelogueService(travelogue_repo, material_repo, share_repo)


class TestTravelogueCrud:
    @pytest.mark.asyncio
    async def test_create_get_and_get_by_trip(self, service, travelogue_repo):
        travelogue = _travelogue()
        travelogue_repo.create_for_trip.return_value = travelogue
        travelogue_repo.get_by_id.return_value = travelogue
        travelogue_repo.get_by_trip.return_value = travelogue

        created = await service.create("trip-1", "user-1", style="diary")
        fetched = await service.get("travelogue-1")
        by_trip = await service.get_by_trip("trip-1")

        assert created["style"] == "diary"
        assert created["photos"] == []
        assert created["created_at"] == "2026-07-17T10:00:00"
        assert fetched["id"] == "travelogue-1"
        assert by_trip["trip_id"] == "trip-1"

    @pytest.mark.asyncio
    async def test_get_methods_return_none_when_missing(self, service):
        assert await service.get("missing") is None
        assert await service.get_by_trip("missing") is None

    @pytest.mark.asyncio
    async def test_list_by_user_returns_paginated_serialized_items(
        self, service, travelogue_repo,
    ):
        travelogue_repo.list_by_user.return_value = [
            _travelogue(updated_at=datetime(2026, 7, 17, 12, 0)),
        ]
        travelogue_repo.count_by_user.return_value = 1

        result = await service.list_by_user(
            "user-1", status="draft", page=2, page_size=5,
        )

        assert isinstance(result, PaginatedData)
        assert result.total == 1
        assert result.list[0]["updated_at"] == "2026-07-17T12:00:00"
        travelogue_repo.list_by_user.assert_awaited_once_with(
            "user-1", "draft", 5, 5,
        )

    @pytest.mark.asyncio
    async def test_update_changes_known_non_none_fields(self, service, travelogue_repo):
        travelogue = _travelogue()
        travelogue_repo.get_by_id.return_value = travelogue

        result = await service.update(
            "travelogue-1",
            user_id="user-1",
            title="新标题",
            content=None,
            unknown="ignored",
        )

        assert result["title"] == "新标题"
        assert result["content"] == "游记正文"
        assert not hasattr(travelogue, "unknown")
        travelogue_repo.update.assert_awaited_once_with(travelogue)

    @pytest.mark.asyncio
    async def test_update_rejects_missing_and_wrong_owner(self, service, travelogue_repo):
        with pytest.raises(ValueError, match="Travelogue not found"):
            await service.update("missing", title="新标题")

        travelogue_repo.get_by_id.return_value = _travelogue(user_id="other-user")
        with pytest.raises(PermissionError, match="Permission denied"):
            await service.update("travelogue-1", user_id="user-1", title="新标题")

    @pytest.mark.asyncio
    async def test_publish_and_delete(self, service, travelogue_repo):
        travelogue_repo.get_by_id.return_value = _travelogue()

        published = await service.publish("travelogue-1", user_id="user-1")
        deleted = await service.delete("travelogue-1")

        assert published["status"] == "published"
        assert deleted is True

    @pytest.mark.asyncio
    async def test_delete_by_user_enforces_ownership(self, service, travelogue_repo):
        with pytest.raises(ValueError, match="Travelogue not found"):
            await service.delete_by_user("missing", "user-1")

        travelogue_repo.get_by_id.return_value = _travelogue(user_id="other-user")
        with pytest.raises(PermissionError, match="Permission denied"):
            await service.delete_by_user("travelogue-1", "user-1")

        travelogue_repo.get_by_id.return_value = _travelogue()
        assert await service.delete_by_user("travelogue-1", "user-1") is True


class TestTravelogueMaterials:
    @pytest.mark.asyncio
    async def test_create_and_list_materials(self, service, material_repo):
        material = _material()
        material_repo.create_material.return_value = material
        material_repo.list_by_trip.return_value = [material]

        created = await service.create_material(
            "trip-1", "user-1", type="xiaohongshu",
        )
        listed = await service.list_materials("trip-1", "xiaohongshu")

        assert created["hashtags"] == []
        assert created["images"] == []
        assert created["created_at"] == "2026-07-17T11:00:00"
        assert listed[0]["source_poi"] == "故宫"

    @pytest.mark.asyncio
    async def test_favorite_material_updates_state(self, service, material_repo):
        material = _material()
        material_repo.get_by_id.return_value = material

        result = await service.favorite_material("material-1", True)

        assert result["is_favorite"] is True
        material_repo.update.assert_awaited_once_with(material)

    @pytest.mark.asyncio
    async def test_favorite_material_rejects_missing_item(self, service):
        with pytest.raises(ValueError, match="Material not found"):
            await service.favorite_material("missing")

    @pytest.mark.asyncio
    async def test_mark_used_updates_state_and_rejects_missing(
        self, service, material_repo,
    ):
        material_repo.get_by_id.return_value = _material()

        result = await service.mark_used_in_travelogue("material-1")

        assert result["used_in_travelogue"] is True

        material_repo.get_by_id.return_value = None
        with pytest.raises(ValueError, match="Material not found"):
            await service.mark_used_in_travelogue("missing")


class TestTravelogueShares:
    @pytest.mark.asyncio
    async def test_create_and_get_share(self, service, share_repo):
        share = _share(
            password="secret",
            expire_at=datetime(2026, 8, 1, 0, 0),
        )
        share_repo.create_share.return_value = share
        share_repo.get_by_code.return_value = share

        created = await service.create_share(
            "user-1",
            "travelogue",
            "travelogue-1",
            "abc123",
            password="secret",
            expire_at=share.expire_at,
        )
        fetched = await service.get_share_by_code("abc123")

        assert created["has_password"] is True
        assert created["expire_at"] == "2026-08-01T00:00:00"
        assert created["share_url"] == "https://travel.example.com/s/abc123"
        assert fetched["target_id"] == "travelogue-1"

    @pytest.mark.asyncio
    async def test_get_share_and_password_return_none_when_missing(self, service):
        assert await service.get_share_by_code("missing") is None
        assert await service.get_share_password("missing") is None

    @pytest.mark.asyncio
    async def test_increment_view_updates_existing_share_only(self, service, share_repo):
        share = _share(view_count=None)
        share_repo.get_by_code.return_value = share

        await service.increment_view("abc123")

        assert share.view_count == 1
        share_repo.update.assert_awaited_once_with(share)

        share_repo.get_by_code.return_value = None
        await service.increment_view("missing")
        assert share_repo.update.await_count == 1

    @pytest.mark.asyncio
    async def test_get_share_password_returns_stored_password(self, service, share_repo):
        share_repo.get_by_code.return_value = _share(password="secret")

        assert await service.get_share_password("abc123") == "secret"
