from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models import Journey, JourneyStop, Route, RouteStop, JourneyStatus, StopStatus


def _get_journey_stops_ordered(journey: Journey) -> list[JourneyStop]:
    return sorted(journey.stops, key=lambda s: s.sequence)


def _compute_counts(stops: list[JourneyStop]) -> tuple[int, int]:
    """Returns (visited_count, total_mandatory_count)"""
    visited = sum(1 for s in stops if s.status == StopStatus.VISITED)
    mandatory = sum(1 for s in stops if not s.route_stop.optional)
    return visited, mandatory


def _find_current_stop(stops: list[JourneyStop]) -> JourneyStop | None:
    for s in stops:
        if s.status in (StopStatus.PENDING, StopStatus.CURRENT):
            s.status = StopStatus.CURRENT
            return s
    return None


def create_journey(db: Session, route_id: str, user_id: str | None, guest_session_id: str | None) -> Journey:
    """Snapshot route stops into journey stops and start the journey."""
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    if route.status.value != "published":
        raise HTTPException(status_code=400, detail="Route is not published")

    journey = Journey(
        route_id=route_id,
        user_id=user_id,
        guest_session_id=guest_session_id,
        status=JourneyStatus.ACTIVE,
        started_at=datetime.utcnow(),
    )
    db.add(journey)
    db.flush()

    # Snapshot stops in configured order
    for rs in sorted(route.stops, key=lambda s: s.sequence):
        js = JourneyStop(
            journey_id=journey.id,
            route_stop_id=rs.id,
            pandal_id=rs.pandal_id,
            sequence=rs.sequence,
            status=StopStatus.PENDING,
        )
        db.add(js)

    db.flush()
    # Mark first stop as CURRENT
    first = db.query(JourneyStop).filter(
        JourneyStop.journey_id == journey.id
    ).order_by(JourneyStop.sequence).first()
    if first:
        first.status = StopStatus.CURRENT

    db.commit()
    db.refresh(journey)
    return journey


def visit_stop(db: Session, journey_id: str, pandal_id: str, action_id: str,
               user_id: str | None, guest_session_id: str | None) -> tuple[Journey, JourneyStop | None]:
    """Mark a stop as visited. Idempotent on action_id."""
    journey = _load_and_authorize(db, journey_id, user_id, guest_session_id)

    if journey.status not in (JourneyStatus.ACTIVE,):
        raise HTTPException(status_code=400, detail=f"Journey is not active (status: {journey.status.value})")

    # Idempotency check
    existing_action = db.query(JourneyStop).filter(
        JourneyStop.journey_id == journey_id,
        JourneyStop.visit_action_id == action_id,
    ).first()
    if existing_action:
        # Already processed - return current state idempotently
        db.refresh(journey)
        next_stop = _find_next_pending(journey)
        return journey, next_stop

    # Find the stop to visit
    jstop = db.query(JourneyStop).filter(
        JourneyStop.journey_id == journey_id,
        JourneyStop.pandal_id == pandal_id,
    ).first()
    if not jstop:
        raise HTTPException(status_code=404, detail="Pandal is not part of this journey")
    if jstop.status == StopStatus.VISITED:
        raise HTTPException(status_code=409, detail="Stop already visited")
    if jstop.status != StopStatus.CURRENT:
        raise HTTPException(status_code=400, detail="Only the current stop can be marked as visited")

    # Record visit
    jstop.status = StopStatus.VISITED
    jstop.visited_at = datetime.utcnow()
    jstop.visit_action_id = action_id

    # Advance to next pending stop
    stops = _get_journey_stops_ordered(journey)
    next_stop = None
    for s in stops:
        if s.id != jstop.id and s.status == StopStatus.PENDING:
            s.status = StopStatus.CURRENT
            next_stop = s
            break

    # Check completion
    mandatory_stops = [s for s in stops if not s.route_stop.optional]
    all_mandatory_done = all(s.status == StopStatus.VISITED for s in mandatory_stops)
    if all_mandatory_done:
        journey.status = JourneyStatus.COMPLETED
        journey.completed_at = datetime.utcnow()
        next_stop = None

    journey.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(journey)
    return journey, next_stop


def pause_journey(db: Session, journey_id: str, user_id: str | None, guest_session_id: str | None) -> Journey:
    journey = _load_and_authorize(db, journey_id, user_id, guest_session_id)
    if journey.status != JourneyStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Only active journeys can be paused")
    journey.status = JourneyStatus.PAUSED
    journey.paused_at = datetime.utcnow()
    journey.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(journey)
    return journey


def resume_journey(db: Session, journey_id: str, user_id: str | None, guest_session_id: str | None) -> Journey:
    journey = _load_and_authorize(db, journey_id, user_id, guest_session_id)
    if journey.status != JourneyStatus.PAUSED:
        raise HTTPException(status_code=400, detail="Only paused journeys can be resumed")
    journey.status = JourneyStatus.ACTIVE
    journey.paused_at = None
    journey.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(journey)
    return journey


def abandon_journey(db: Session, journey_id: str, user_id: str | None, guest_session_id: str | None) -> Journey:
    journey = _load_and_authorize(db, journey_id, user_id, guest_session_id)
    if journey.status in (JourneyStatus.COMPLETED, JourneyStatus.ABANDONED):
        raise HTTPException(status_code=400, detail=f"Cannot abandon journey with status {journey.status.value}")
    journey.status = JourneyStatus.ABANDONED
    journey.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(journey)
    return journey


def _load_and_authorize(db: Session, journey_id: str, user_id: str | None, guest_session_id: str | None) -> Journey:
    journey = db.query(Journey).filter(Journey.id == journey_id).first()
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")
    # Authorization
    if user_id:
        if journey.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
    elif guest_session_id:
        if journey.guest_session_id != guest_session_id:
            raise HTTPException(status_code=403, detail="Access denied")
    else:
        raise HTTPException(status_code=401, detail="Authentication required")
    return journey


def _find_next_pending(journey: Journey) -> JourneyStop | None:
    for s in sorted(journey.stops, key=lambda x: x.sequence):
        if s.status == StopStatus.CURRENT:
            return s
    return None


def enrich_journey(journey: Journey) -> dict:
    stops = sorted(journey.stops, key=lambda s: s.sequence)
    visited_count = sum(1 for s in stops if s.status == StopStatus.VISITED)
    current = next((s for s in stops if s.status == StopStatus.CURRENT), None)
    return {
        "visited_count": visited_count,
        "total_count": len(stops),
        "current_stop": current,
    }
