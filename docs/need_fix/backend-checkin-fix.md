# 后端签到功能修复方案

> 基于 2026-07-14 代码审查，按修复优先级排序

---

## 🔴 P0 — 运行时崩溃

### B1. `Checkin` 模型缺少 `source_day` 列

**现象**：API `GET /trips/{id}/checkins?day=1` 调用 `list_by_trip(day=1)` 时抛出 SQLAlchemy `InvalidRequestError`。

**根因**：`app/db/repositories/trip_repo.py:71` 引用了 `Checkin.source_day`，但 `app/db/models/trip.py` 的 `Checkin` 模型从未定义该列。

`source_day` 在全链路中已被广泛使用：

| 文件 | 用途 |
|---|---|
| `app/agents/travelogue_agent.py:59,137,428,492` | 按天分组签到数据生成游记/素材 |
| `app/agents/trip_agent.py:83-136` | `process_checkin` 处理签到事件（传入 `source_day`） |
| `app/schemas/travelogue.py:52` | `SocialMaterial` schema 已定义 |
| `app/db/models/travelogue.py:61` | `SocialMaterial` 模型已定义 ✅ |
| `frontend/src/api/travelogue.ts:37` | 前端类型已定义 |
| `scripts/test_v2_execution.py:137` | 测试数据已传入 |
| `scripts/test_agents.py:160` | 测试数据已传入 |

**修复**：给 `Checkin` 模型添加 `source_day` 列。

**涉及文件**：
- [app/db/models/trip.py](app/db/models/trip.py) — 新增列
- [app/schemas/trip.py](app/schemas/trip.py) — `CheckinCreateRequest` / `CheckinResponse` 补充字段
- [app/db/repositories/trip_repo.py](app/db/repositories/trip_repo.py) — 无需修改（已有引用）
- [app/api/v1/trip.py](app/api/v1/trip.py) — 无需修改（已有 `day` 参数）
- [app/services/application/trip_service.py](app/services/application/trip_service.py) — `_checkin_to_dict` 序列化补充字段
- 需要生成数据库迁移（新增列）

**修改内容**：

```python
# app/db/models/trip.py — Checkin 类新增
source_day = Column(Integer, nullable=True, doc="签到所属第几天（从方案 daily_itinerary 提取）")

# app/schemas/trip.py — CheckinCreateRequest 新增可选
source_day: int | None = None

# app/schemas/trip.py — CheckinResponse 新增
source_day: int | None = None

# app/services/application/trip_service.py — _checkin_to_dict 新增
"source_day": c.source_day,
```

---

### B2. `total_pois` 从未从方案初始化

**现象**：创建行程后，进度始终为 `x/0`（实际 `max(total_pois, 1)` 兜底显示 `x/1`），进度条无参考价值。

**根因**：`TripRepository.create_for_plan()` (`app/db/repositories/trip_repo.py:19-27`) 只设了 `status/started_at/budget`，`total_pois` 默认为 0。`TripAgent.start_trip()` (`app/agents/trip_agent.py:41-79`) 已经实现了 POI 计数逻辑，但结果从未持久化到 DB。

**修复**：在 `TripService.start_trip()` 中调用 `TripAgent` 或直接计算 POI 数后写入 `total_pois`。

**涉及文件**：
- [app/services/application/trip_service.py](app/services/application/trip_service.py) — `start_trip()` 方法

**修改内容**：

```python
async def start_trip(self, user_id: str, plan_id: str, budget_total: float = 0) -> dict:
    # 1. 查询关联方案获取 daily_itinerary
    plan = await self.plan_repo.get_by_id(plan_id)
    total_pois = 0
    budget_total = 0
    if plan and plan.daily_itinerary:
        for day in plan.daily_itinerary:
            total_pois += len(day.get("activities", []))
            total_pois += len(day.get("meals", []))
        budget_total = plan.total_budget or 0

    # 2. 创建行程时传入 total_pois
    trip = await self.trip_repo.create_for_plan(
        user_id, plan_id, total_pois=total_pois, budget_total=budget_total,
    )
    return self._trip_to_dict(trip)
```

同时修改 `TripRepository.create_for_plan()` 接受 `total_pois` 参数：

```python
async def create_for_plan(self, user_id: str, plan_id: str,
                          total_pois: int = 0, budget_total: float = 0) -> TripState:
    trip = TripState(
        plan_id=plan_id, user_id=user_id,
        status="active", total_pois=total_pois,
        budget_total=budget_total, budget_remain=budget_total, budget_spent=0,
        started_at=datetime.utcnow(),
    )
    return await self.create(trip)
```

---

## 🟡 P1 — 功能缺陷

### B3. `actual_at` 类型不一致导致签到可能失败

**现象**：前端传入的 `actual_at` 是 ISO 字符串，DB 模型列是 `DateTime`。通过 `**kwargs` 直接传给 SQLAlchemy 构造器时，不同数据库驱动行为不同（SQLite 可能静默接受，PostgreSQL 抛错）。

**根因**（[app/schemas/trip.py:60](app/schemas/trip.py#L60) vs [app/db/models/trip.py:73](app/db/models/trip.py#L73)）：

```python
# Schema
actual_at: str | None = None       # 字符串
# 模型
actual_at = Column(DateTime, ...)  # DateTime
```

**修复**：在 `TripService.checkin()` 中做类型转换，或者给 Schema 增加 validator。

**涉及文件**：
- [app/schemas/trip.py](app/schemas/trip.py) — 增加 Pydantic validator
- [app/services/application/trip_service.py](app/services/application/trip_service.py) — `checkin()` 中预处理

**推荐方案（Schema validator）**：

```python
from pydantic import field_validator
from datetime import datetime

class CheckinCreateRequest(BaseModel):
    # ... 现有字段
    
    @field_validator("actual_at", mode="before")
    @classmethod
    def parse_actual_at(cls, v):
        if isinstance(v, str):
            return v  # 保持字符串，由 service 层转换
        return v
```

或在 Service 层转换：

```python
# app/services/application/trip_service.py checkin() 中
if isinstance(kwargs.get("actual_at"), str):
    kwargs["actual_at"] = datetime.fromisoformat(kwargs["actual_at"])
```

---

### B4. `list_adjustments` 分页总数计算错误

**现象**：`GET /trips/{id}/adjustments?page=2` 的总数 `total` 始终等于返回列表长度，而非总记录数。

**根因**（[app/services/application/trip_service.py:163](app/services/application/trip_service.py#L163)）：

```python
total = len(adjs)  # ❌ 这是当前页长度，不是总数
```

**修复**：

```python
total = await self.adj_repo.count_by_trip(trip_id, status)
```

并给 `AdjustmentRepository` 增加 `count_by_trip` 方法：

```python
# app/db/repositories/trip_repo.py AdjustmentRepository 类
async def count_by_trip(self, trip_id: str, status: str | None = None) -> int:
    return await self.count(trip_id=trip_id, status=status)
```

---

### B5. `TripAgent.process_checkin` 缺少 day 推进逻辑

**现象**：多次签到后 `TripState.current_day` 永远不会自增，始终停留在第 1 天。

**根因**：`process_checkin()` 返回 `time_delta_min` / `trigger_adjustment` 等指标，但不会更新行程的 `current_day`。只有 `TripService.checkin()` 会增加 `checked_in` 计数，但不会推进天数。

**修复方案**：在 `TripService.checkin()` 中，当 `source_day > current_day` 时自动推进：

```python
# app/services/application/trip_service.py checkin() 中
source_day = kwargs.get("source_day")
if source_day and trip.current_day and source_day > trip.current_day:
    trip.current_day = source_day
```

---

## 🔵 P2 — 健壮性改进

### B6. `CheckinCreateRequest` 缺少字段校验

**现象**：`poi_type` 仅靠 docstring 说明，没有枚举校验，无效值会直接入库。

**修复**：

```python
class CheckinCreateRequest(BaseModel):
    poi_type: str = Field(..., pattern=r"^(attraction|restaurant|hotel|other)$",
                          description="签到类型枚举")
```

### B7. 照片字段语义模糊

**现象**：`photos` 默认 `list[dict]`，但没约束 dict 结构，前端可能传入任意形状。

**修复**：创建 `PhotoSchema` sub-model：

```python
class PhotoSchema(BaseModel):
    url: str
    thumbnail_url: str | None = None
    ai_caption: str | None = None
    ai_tags: list[str] = []
    quality_score: float | None = Field(None, ge=0, le=1)

class CheckinCreateRequest(BaseModel):
    photos: list[PhotoSchema] = []
```

### B8. `trip_repo.py` 缺少迁移文件

**现象**：以上模型变更需对应迁移文件。项目若使用 Alembic 则需生成迁移。

**操作**：
```bash
alembic revision --autogenerate -m "add checkin source_day column"
alembic upgrade head
```

---

## 📋 修改清单

| ID | 文件 | 变更类型 | 优先级 |
|---|---|---|---|
| B1 | `app/db/models/trip.py` | +1 列 `source_day` | P0 🔴 |
| B1 | `app/schemas/trip.py` | +2 字段（req/resp） | P0 🔴 |
| B1 | `app/services/application/trip_service.py` | +1 序列化字段 | P0 🔴 |
| B1 | 迁移文件 | 新增 | P0 🔴 |
| B2 | `app/services/application/trip_service.py` | 修改 `start_trip()` | P1 🟡 |
| B2 | `app/db/repositories/trip_repo.py` | 修改 `create_for_plan()` | P1 🟡 |
| B3 | `app/schemas/trip.py` / `trip_service.py` | 加 validator / 类型转换 | P1 🟡 |
| B4 | `app/db/repositories/trip_repo.py` | +`count_by_trip()` | P1 🟡 |
| B4 | `app/services/application/trip_service.py` | 修正 `list_adjustments` 计数 | P1 🟡 |
| B5 | `app/services/application/trip_service.py` | 签到后推进 `current_day` | P1 🟡 |
| B6 | `app/schemas/trip.py` | 加 `pattern` 枚举校验 | P2 🔵 |
| B7 | `app/schemas/trip.py` | 创建 `PhotoSchema` 子模型 | P2 🔵 |
| B8 | 迁移文件 | 全部变更的统一迁移 | P2 🔵 |
