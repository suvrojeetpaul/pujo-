from datetime import datetime
from typing import Any
from pydantic import BaseModel, EmailStr, field_validator
from app.models import Region, RouteStatus, JourneyStatus, StopStatus


# ── Common ───────────────────────────────────────────────────────────────────

class ApiResponse(BaseModel):
    success: bool = True
    data: Any = None
    message: str | None = None


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    limit: int
    offset: int


# ── Auth ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    is_admin: bool


class GuestSessionResponse(BaseModel):
    guest_session_id: str
    token: str


# ── Pandal ───────────────────────────────────────────────────────────────────

class PandalBase(BaseModel):
    name: str
    region: Region
    address: str
    latitude: float | None = None
    longitude: float | None = None
    description: str | None = None
    image_url: str | None = None
    opening_hours: str | None = None
    accessibility_notes: str | None = None
    suggested_visit_duration_minutes: int | None = None


class PandalCreate(PandalBase):
    @field_validator("latitude")
    @classmethod
    def validate_lat(cls, v: float | None) -> float | None:
        if v is not None and not (-90 <= v <= 90):
            raise ValueError("Latitude must be between -90 and 90")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_lon(cls, v: float | None) -> float | None:
        if v is not None and not (-180 <= v <= 180):
            raise ValueError("Longitude must be between -180 and 180")
        return v


class PandalUpdate(PandalCreate):
    name: str | None = None
    region: Region | None = None
    address: str | None = None


class PandalOut(PandalBase):
    id: str
    last_verified_at: datetime | None
    is_fictional: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Route ────────────────────────────────────────────────────────────────────

class RouteStopOut(BaseModel):
    id: str
    pandal_id: str
    sequence: int
    distance_from_previous_meters: float | None
    estimated_travel_minutes: int | None
    optional: bool
    stop_notes: str | None
    pandal: PandalOut

    model_config = {"from_attributes": True}


class RouteBase(BaseModel):
    name: str
    region: Region
    description: str | None = None
    cover_image_url: str | None = None
    total_distance_meters: float | None = None
    estimated_duration_minutes: int | None = None


class RouteCreate(RouteBase):
    slug: str


class RouteUpdate(RouteBase):
    name: str | None = None
    region: Region | None = None


class RouteOut(RouteBase):
    id: str
    slug: str
    status: RouteStatus
    start_pandal_id: str | None
    end_pandal_id: str | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime
    stop_count: int = 0

    model_config = {"from_attributes": True}


class RouteDetailOut(RouteOut):
    stops: list[RouteStopOut] = []


# ── Journey ───────────────────────────────────────────────────────────────────

class JourneyStopOut(BaseModel):
    id: str
    route_stop_id: str
    pandal_id: str
    sequence: int
    status: StopStatus
    visited_at: datetime | None
    skipped_at: datetime | None
    pandal: PandalOut

    model_config = {"from_attributes": True}


class JourneyOut(BaseModel):
    id: str
    route_id: str
    user_id: str | None
    guest_session_id: str | None
    status: JourneyStatus
    started_at: datetime | None
    paused_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    visited_count: int = 0
    total_count: int = 0
    current_stop: JourneyStopOut | None = None
    route: RouteOut | None = None
    stops: list[JourneyStopOut] = []

    model_config = {"from_attributes": True}


class VisitRequest(BaseModel):
    action_id: str  # client-generated idempotency key (UUID)


class VisitResponse(BaseModel):
    journey: JourneyOut
    next_stop: JourneyStopOut | None
    message: str


class CreateJourneyRequest(BaseModel):
    route_id: str


# ── Admin Import ──────────────────────────────────────────────────────────────

class ImportStopSchema(BaseModel):
    pandal_name: str
    sequence: int
    distance_from_previous_meters: float | None = None
    estimated_travel_minutes: int | None = None
    optional: bool = False
    stop_notes: str | None = None
    address: str
    latitude: float | None = None
    longitude: float | None = None
    description: str | None = None
    image_url: str | None = None
    region: Region


class ImportRouteSchema(BaseModel):
    name: str
    slug: str
    region: Region
    description: str | None = None
    cover_image_url: str | None = None
    total_distance_meters: float | None = None
    estimated_duration_minutes: int | None = None
    stops: list[ImportStopSchema]


class ImportRequest(BaseModel):
    routes: list[ImportRouteSchema]
    dry_run: bool = True


class ImportResult(BaseModel):
    errors: list[str]
    warnings: list[str]
    routes_to_import: int
    stops_to_import: int
    is_valid: bool
