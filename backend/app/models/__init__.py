import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    String, Text, Float, Integer, Boolean, DateTime,
    ForeignKey, Enum as SAEnum, UniqueConstraint, CheckConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def new_uuid() -> str:
    return str(uuid.uuid4())


def now_utc() -> datetime:
    return datetime.utcnow()


# ── Enums ────────────────────────────────────────────────────────────────────

class Region(str, enum.Enum):
    NORTH = "north"
    SOUTH = "south"


class RouteStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class JourneyStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class StopStatus(str, enum.Enum):
    PENDING = "pending"
    CURRENT = "current"
    VISITED = "visited"
    SKIPPED = "skipped"


# ── Models ───────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, onupdate=now_utc)

    journeys: Mapped[list["Journey"]] = relationship("Journey", back_populates="user")


class Pandal(Base):
    __tablename__ = "pandals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    region: Mapped[Region] = mapped_column(SAEnum(Region), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(512))
    opening_hours: Mapped[str | None] = mapped_column(String(255))
    accessibility_notes: Mapped[str | None] = mapped_column(Text)
    suggested_visit_duration_minutes: Mapped[int | None] = mapped_column(Integer)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    is_fictional: Mapped[bool] = mapped_column(Boolean, default=False)  # dev fixtures flag
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, onupdate=now_utc)

    route_stops: Mapped[list["RouteStop"]] = relationship("RouteStop", back_populates="pandal")


class Route(Base):
    __tablename__ = "routes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    region: Mapped[Region] = mapped_column(SAEnum(Region), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[RouteStatus] = mapped_column(SAEnum(RouteStatus), default=RouteStatus.DRAFT)
    cover_image_url: Mapped[str | None] = mapped_column(String(512))
    start_pandal_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("pandals.id"))
    end_pandal_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("pandals.id"))
    total_distance_meters: Mapped[float | None] = mapped_column(Float)
    estimated_duration_minutes: Mapped[int | None] = mapped_column(Integer)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, onupdate=now_utc)

    stops: Mapped[list["RouteStop"]] = relationship(
        "RouteStop", back_populates="route", order_by="RouteStop.sequence", cascade="all, delete-orphan"
    )
    journeys: Mapped[list["Journey"]] = relationship("Journey", back_populates="route")
    start_pandal: Mapped["Pandal | None"] = relationship("Pandal", foreign_keys=[start_pandal_id])
    end_pandal: Mapped["Pandal | None"] = relationship("Pandal", foreign_keys=[end_pandal_id])

    __table_args__ = (
        CheckConstraint("total_distance_meters >= 0", name="ck_route_distance_nonneg"),
        CheckConstraint("estimated_duration_minutes >= 0", name="ck_route_duration_nonneg"),
    )


class RouteStop(Base):
    __tablename__ = "route_stops"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    route_id: Mapped[str] = mapped_column(String(36), ForeignKey("routes.id", ondelete="CASCADE"), nullable=False)
    pandal_id: Mapped[str] = mapped_column(String(36), ForeignKey("pandals.id"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    distance_from_previous_meters: Mapped[float | None] = mapped_column(Float)
    estimated_travel_minutes: Mapped[int | None] = mapped_column(Integer)
    optional: Mapped[bool] = mapped_column(Boolean, default=False)
    stop_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)

    route: Mapped["Route"] = relationship("Route", back_populates="stops")
    pandal: Mapped["Pandal"] = relationship("Pandal", back_populates="route_stops")

    __table_args__ = (
        UniqueConstraint("route_id", "sequence", name="uq_route_stop_sequence"),
        UniqueConstraint("route_id", "pandal_id", name="uq_route_pandal"),
        CheckConstraint("sequence >= 1", name="ck_stop_sequence_positive"),
        CheckConstraint("distance_from_previous_meters >= 0", name="ck_stop_distance_nonneg"),
        CheckConstraint("estimated_travel_minutes >= 0", name="ck_stop_travel_nonneg"),
        Index("ix_route_stop_route_seq", "route_id", "sequence"),
    )


class Journey(Base):
    __tablename__ = "journeys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    route_id: Mapped[str] = mapped_column(String(36), ForeignKey("routes.id"), nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    guest_session_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    status: Mapped[JourneyStatus] = mapped_column(SAEnum(JourneyStatus), default=JourneyStatus.NOT_STARTED)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, onupdate=now_utc)

    route: Mapped["Route"] = relationship("Route", back_populates="journeys")
    user: Mapped["User | None"] = relationship("User", back_populates="journeys")
    stops: Mapped[list["JourneyStop"]] = relationship(
        "JourneyStop", back_populates="journey", order_by="JourneyStop.sequence", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_journey_guest", "guest_session_id"),
        Index("ix_journey_user", "user_id"),
    )


class JourneyStop(Base):
    __tablename__ = "journey_stops"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    journey_id: Mapped[str] = mapped_column(String(36), ForeignKey("journeys.id", ondelete="CASCADE"), nullable=False)
    route_stop_id: Mapped[str] = mapped_column(String(36), ForeignKey("route_stops.id"), nullable=False)
    pandal_id: Mapped[str] = mapped_column(String(36), ForeignKey("pandals.id"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[StopStatus] = mapped_column(SAEnum(StopStatus), default=StopStatus.PENDING)
    visited_at: Mapped[datetime | None] = mapped_column(DateTime)
    skipped_at: Mapped[datetime | None] = mapped_column(DateTime)
    visit_action_id: Mapped[str | None] = mapped_column(String(36), unique=True)  # idempotency key
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)

    journey: Mapped["Journey"] = relationship("Journey", back_populates="stops")
    pandal: Mapped["Pandal"] = relationship("Pandal")
    route_stop: Mapped["RouteStop"] = relationship("RouteStop")

    __table_args__ = (
        UniqueConstraint("journey_id", "sequence", name="uq_journey_stop_sequence"),
        UniqueConstraint("journey_id", "pandal_id", name="uq_journey_pandal"),
        CheckConstraint("sequence >= 1", name="ck_journey_stop_seq_positive"),
        Index("ix_journey_stop_journey_seq", "journey_id", "sequence"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(36))
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
