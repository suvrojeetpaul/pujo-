from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Journey, JourneyStatus, User, JourneyStop
from app.schemas import CreateJourneyRequest, JourneyOut, VisitRequest, VisitResponse
from app.services.auth import get_identity
from app.services.journey import (
    abandon_journey,
    create_journey,
    enrich_journey,
    pause_journey,
    resume_journey,
    visit_stop,
)

router = APIRouter(prefix="/journeys", tags=["journeys"])


@router.post("", response_model=JourneyOut, status_code=status.HTTP_201_CREATED)
def start_journey(
    payload: CreateJourneyRequest,
    identity: tuple[str | None, str | None] = Depends(get_identity),
    db: Session = Depends(get_db),
) -> Journey:
    user_id, guest_session_id = identity
    return _journey_out(create_journey(db, payload.route_id, user_id, guest_session_id))


@router.get("/{journey_id}", response_model=JourneyOut)
def get_journey(
    journey_id: str,
    identity: tuple[str | None, str | None] = Depends(get_identity),
    db: Session = Depends(get_db),
) -> Journey:
    user_id, guest_session_id = identity
    journey = _load_journey(db, journey_id)
    _check_owner(journey, user_id, guest_session_id)
    return _journey_out(journey)


@router.post("/{journey_id}/stops/{pandal_id}/visit", response_model=VisitResponse)
def mark_visited(
    journey_id: str,
    pandal_id: str,
    payload: VisitRequest,
    identity: tuple[str | None, str | None] = Depends(get_identity),
    db: Session = Depends(get_db),
) -> VisitResponse:
    user_id, guest_session_id = identity
    journey, next_stop = visit_stop(db, journey_id, pandal_id, payload.action_id, user_id, guest_session_id)
    return VisitResponse(
        journey=_journey_out(journey),
        next_stop=next_stop,
        message="Stop marked as visited" if next_stop else "Journey completed",
    )


@router.post("/{journey_id}/pause", response_model=JourneyOut)
def pause(
    journey_id: str,
    identity: tuple[str | None, str | None] = Depends(get_identity),
    db: Session = Depends(get_db),
) -> Journey:
    return _journey_out(pause_journey(db, journey_id, *identity))


@router.post("/{journey_id}/resume", response_model=JourneyOut)
def resume(
    journey_id: str,
    identity: tuple[str | None, str | None] = Depends(get_identity),
    db: Session = Depends(get_db),
) -> Journey:
    return _journey_out(resume_journey(db, journey_id, *identity))


@router.post("/{journey_id}/abandon", response_model=JourneyOut)
def abandon(
    journey_id: str,
    identity: tuple[str | None, str | None] = Depends(get_identity),
    db: Session = Depends(get_db),
) -> Journey:
    return _journey_out(abandon_journey(db, journey_id, *identity))


def _load_journey(db: Session, journey_id: str) -> Journey:
    journey = (
        db.query(Journey)
        .options(
            selectinload(Journey.stops).selectinload(JourneyStop.pandal),
            selectinload(Journey.stops).selectinload(JourneyStop.route_stop),
            selectinload(Journey.route),
        )
        .filter(Journey.id == journey_id)
        .first()
    )
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")
    return journey


def _check_owner(journey: Journey, user_id: str | None, guest_session_id: str | None) -> None:
    if user_id and journey.user_id == user_id:
        return
    if guest_session_id and journey.guest_session_id == guest_session_id:
        return
    raise HTTPException(status_code=403, detail="Access denied")


def _journey_out(journey: Journey):
    response = JourneyOut.model_validate(journey)
    stats = enrich_journey(journey)
    response.visited_count = stats["visited_count"]
    response.total_count = stats["total_count"]
    response.current_stop = stats["current_stop"]
    return response
