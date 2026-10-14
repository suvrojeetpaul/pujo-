from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Region, Route, RouteStatus, Pandal, RouteStop
from app.schemas import PandalOut, RouteDetailOut, RouteOut

router = APIRouter(tags=["routes"])


@router.get("/routes", response_model=list[RouteOut])
def list_routes(
    region: Region | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[RouteOut]:
    query = db.query(Route).filter(Route.status == RouteStatus.PUBLISHED)
    if region:
        query = query.filter(Route.region == region)
    routes = query.order_by(Route.region, Route.name).all()
    return [_route_out(route) for route in routes]


@router.get("/routes/{route_id}", response_model=RouteDetailOut)
def get_route(route_id: str, db: Session = Depends(get_db)) -> Route:
    route = (
        db.query(Route)
        .options(selectinload(Route.stops).selectinload(RouteStop.pandal))
        .filter(Route.id == route_id, Route.status == RouteStatus.PUBLISHED)
        .first()
    )
    if not route:
        raise HTTPException(status_code=404, detail="Published route not found")
    return route


@router.get("/pandals/{pandal_id}", response_model=PandalOut)
def get_pandal(pandal_id: str, db: Session = Depends(get_db)) -> Pandal:
    pandal = db.query(Pandal).filter(Pandal.id == pandal_id).first()
    if not pandal:
        raise HTTPException(status_code=404, detail="Pandal not found")
    return pandal


def _route_out(route: Route) -> RouteOut:
    return RouteOut(
        **{key: getattr(route, key) for key in (
            "id", "slug", "name", "region", "description", "cover_image_url",
            "total_distance_meters", "estimated_duration_minutes", "status",
            "start_pandal_id", "end_pandal_id", "published_at", "created_at", "updated_at",
        )},
        stop_count=len(route.stops),
    )
