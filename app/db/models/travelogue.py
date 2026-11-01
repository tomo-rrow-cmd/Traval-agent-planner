"""
V2.0 游记 & 社交素材 & 分享表 — travelogues / social_materials / shares
"""

from sqlalchemy import Column, String, Integer, Float, Text, DateTime, JSON, Boolean, ForeignKey

from app.db.models.base import Base, UUIDMixin, TimestampMixin


class Travelogue(Base, UUIDMixin, TimestampMixin):
    """游记 — 基于签到数据 + AI 润色生成"""

    __tablename__ = "travelogues"

    trip_id = Column(String(36), ForeignKey("trip_states.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    title = Column(String(200), nullable=True, doc="游记标题")
    content = Column(Text, nullable=True, doc="Markdown 正文")
    cover_url = Column(String(500), nullable=True, doc="封面图 URL")
    style = Column(String(20), default="diary", nullable=False, doc="diary / xiaohongshu / guide")

    # 图片集
    photos = Column(JSON, default=list, doc='[url]')

    # 统计
    total_days = Column(Integer, nullable=True)
    total_pois = Column(Integer, nullable=True)
    total_cost = Column(Float, nullable=True)
    total_photos = Column(Integer, default=0)

    # 发布状态: draft / published / shared
    status = Column(String(20), default="draft", nullable=False)


class SocialMaterial(Base, UUIDMixin, TimestampMixin):
    """社交素材 — 朋友圈9宫格/旅行卡片/精选合集"""

    __tablename__ = "social_materials"

    trip_id = Column(String(36), ForeignKey("trip_states.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    # 素材类型
    type = Column(String(30), nullable=False,
                  doc="moment_9grid / single_card / day_summary / collage / trip_highlight / budget_card")

    # 文字内容
    title = Column(String(200), nullable=True, doc="朋友圈文案/标题")
    content = Column(Text, nullable=True, doc="正文/描述")
    hashtags = Column(JSON, default=list, doc='["#北京旅行","#故宫"]')
    location_tag = Column(String(200), nullable=True, doc="定位标签")

    # 图片组合
    images = Column(JSON, nullable=False, doc='[{"url":"...","caption":"...","order":1,"is_cover":true}]')
    layout = Column(String(20), nullable=True, doc="grid_9 / grid_4 / single_v / single_h / card")

    # 旅行数据水印（叠加图上的旅行数据）
    overlay_data = Column(JSON, nullable=True, doc='{"steps":15000,"day":"2/5","pois":6,"distance":"12km"}')

    # 来源
    source_day = Column(Integer, nullable=True, doc="来源天数")
    source_poi = Column(String(200), nullable=True, doc="来源景点")

    # 状态
    is_generated = Column(Boolean, default=False, doc="AI 已生成")
    is_favorite = Column(Boolean, default=False, doc="用户收藏")
    used_in_travelogue = Column(Boolean, default=False, doc="已被游记引用")


class Share(Base, UUIDMixin, TimestampMixin):
    """分享链接"""

    __tablename__ = "shares"

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    # 分享目标
    target_type = Column(String(20), nullable=False, doc="plan / travelogue")
    target_id = Column(String(36), nullable=False)

    # 短链接
    share_code = Column(String(20), unique=True, nullable=False, doc="分享短码")
    password = Column(String(100), nullable=True, doc="可选访问密码")

    # 期限 & 统计
    expire_at = Column(DateTime, nullable=True)
    view_count = Column(Integer, default=0)
