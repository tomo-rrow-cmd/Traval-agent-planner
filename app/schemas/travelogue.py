"""游记 & 社交素材 Pydantic Schemas"""

from typing import Literal

from pydantic import BaseModel, Field


# ========== Travelogue ==========

class TravelogueGenerateRequest(BaseModel):
    trip_id: str = Field(...)
    style: Literal["diary", "xiaohongshu", "guide"] = "diary"
    regenerate: bool = False

class TravelogueUpdateRequest(BaseModel):
    title: str | None = None
    content: str | None = None
    cover_url: str | None = None
    style: str = "diary"
    status: str | None = None

class TravelogueResponse(BaseModel):
    id: str
    trip_id: str
    user_id: str
    title: str | None = None
    content: str | None = None
    cover_url: str | None = None
    style: str = "diary"
    photos: list[str] = []
    total_days: int | None = None
    total_pois: int | None = None
    total_cost: float | None = None
    total_photos: int = 0
    status: str = "draft"
    created_at: str | None = None
    updated_at: str | None = None


# ========== Social Material ==========

class MaterialGenerateRequest(BaseModel):
    trip_id: str = Field(...)

class MaterialResponse(BaseModel):
    id: str
    trip_id: str
    user_id: str
    type: str
    title: str | None = None
    content: str | None = None
    hashtags: list[str] = []
    location_tag: str | None = None
    images: list[dict] = []
    layout: str | None = None
    overlay_data: dict | None = None
    source_day: int | None = None
    source_poi: str | None = None
    is_generated: bool = False
    is_favorite: bool = False
    used_in_travelogue: bool = False
    created_at: str | None = None

class MaterialFavoriteRequest(BaseModel):
    is_favorite: bool = True


# ========== Regenerate Section ==========

class RegenerateSectionRequest(BaseModel):
    day: int = Field(..., ge=1, description="要重写的天数")
    style: str = Field(default="diary", description="diary / xiaohongshu / guide")
    feedback: str | None = Field(default=None, description="用户反馈/修改意见")
