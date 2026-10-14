"""Seed the route plans supplied with the application."""
import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import Pandal, Route, RouteStatus, RouteStop, Region


def seed_2026_routes(db: Session) -> None:
    if db.query(Route).count():
        return

    fixture_path = Path(__file__).parents[2] / "fixtures" / "routes_2026.json"
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    for route_data in data["routes"]:
        route = Route(
            slug=route_data["slug"],
            name=route_data["name"],
            region=Region(route_data["region"]),
            description=route_data["description"],
            status=RouteStatus.PUBLISHED,
        )
        db.add(route)
        db.flush()
        for stop_data in route_data["stops"]:
            pandal = Pandal(
                name=stop_data["pandal_name"],
                region=Region(stop_data["region"]),
                address=stop_data["address"],
                is_fictional=False,
            )
            db.add(pandal)
            db.flush()
            db.add(RouteStop(
                route_id=route.id,
                pandal_id=pandal.id,
                sequence=stop_data["sequence"],
                distance_from_previous_meters=stop_data.get("distance_from_previous_meters"),
                estimated_travel_minutes=stop_data.get("estimated_travel_minutes"),
                stop_notes=stop_data.get("stop_notes"),
            ))
            if stop_data["sequence"] == 1:
                route.start_pandal_id = pandal.id
            route.end_pandal_id = pandal.id
    db.commit()
