"""Route data import/validation service."""
from app.schemas import ImportRequest, ImportResult, ImportRouteSchema
from sqlalchemy.orm import Session
from app.models import Pandal, Route, RouteStop, Region
import re


def validate_import(data: ImportRequest) -> ImportResult:
    errors: list[str] = []
    warnings: list[str] = []
    total_stops = 0

    for ri, route in enumerate(data.routes):
        prefix = f"Route[{ri}] '{route.name}'"

        if not route.slug or not re.match(r"^[a-z0-9-]+$", route.slug):
            errors.append(f"{prefix}: slug must be lowercase alphanumeric with hyphens only")

        if not route.stops:
            errors.append(f"{prefix}: must have at least one stop")
            continue

        seqs = [s.sequence for s in route.stops]
        if len(seqs) != len(set(seqs)):
            errors.append(f"{prefix}: duplicate sequence numbers found")

        seqs_sorted = sorted(seqs)
        if seqs_sorted != list(range(1, len(seqs) + 1)):
            errors.append(f"{prefix}: sequence numbers must be consecutive starting at 1, got {seqs_sorted}")

        seen_names = set()
        for si, stop in enumerate(sorted(route.stops, key=lambda s: s.sequence)):
            sprefix = f"{prefix} Stop[{stop.sequence}] '{stop.pandal_name}'"

            if stop.pandal_name in seen_names:
                errors.append(f"{prefix}: duplicate pandal '{stop.pandal_name}'")
            seen_names.add(stop.pandal_name)

            if stop.distance_from_previous_meters is not None and stop.distance_from_previous_meters < 0:
                errors.append(f"{sprefix}: distance cannot be negative")

            if stop.estimated_travel_minutes is not None and stop.estimated_travel_minutes < 0:
                errors.append(f"{sprefix}: travel time cannot be negative")

            if stop.latitude is not None and not (-90 <= stop.latitude <= 90):
                errors.append(f"{sprefix}: latitude out of range")

            if stop.longitude is not None and not (-180 <= stop.longitude <= 180):
                errors.append(f"{sprefix}: longitude out of range")

            if stop.region != route.region:
                warnings.append(f"{sprefix}: stop region '{stop.region}' differs from route region '{route.region}'")

        total_stops += len(route.stops)

        if route.total_distance_meters is not None and route.total_distance_meters < 0:
            errors.append(f"{prefix}: total_distance_meters cannot be negative")

    return ImportResult(
        errors=errors,
        warnings=warnings,
        routes_to_import=len(data.routes),
        stops_to_import=total_stops,
        is_valid=len(errors) == 0,
    )


def execute_import(data: ImportRequest, db: Session) -> dict:
    """Transactionally import validated routes."""
    validation = validate_import(data)
    if not validation.is_valid:
        return {"success": False, "errors": validation.errors}

    imported_routes = []
    for route_data in data.routes:
        # Check if slug exists
        existing = db.query(Route).filter(Route.slug == route_data.slug).first()
        if existing:
            # Archive old, create new version
            existing.status = existing.status  # keep as-is, admin must republish

        # Create pandals and route
        route = Route(
            slug=route_data.slug,
            name=route_data.name,
            region=route_data.region,
            description=route_data.description,
            cover_image_url=route_data.cover_image_url,
            total_distance_meters=route_data.total_distance_meters,
            estimated_duration_minutes=route_data.estimated_duration_minutes,
        )
        db.add(route)
        db.flush()

        sorted_stops = sorted(route_data.stops, key=lambda s: s.sequence)
        pandal_ids: list[str] = []

        for stop_data in sorted_stops:
            # Find or create pandal by name+region
            pandal = db.query(Pandal).filter(
                Pandal.name == stop_data.pandal_name,
                Pandal.region == stop_data.region,
            ).first()
            if not pandal:
                pandal = Pandal(
                    name=stop_data.pandal_name,
                    region=stop_data.region,
                    address=stop_data.address,
                    latitude=stop_data.latitude,
                    longitude=stop_data.longitude,
                    description=stop_data.description,
                    image_url=stop_data.image_url,
                    is_fictional=False,
                )
                db.add(pandal)
                db.flush()
            pandal_ids.append(pandal.id)

            rs = RouteStop(
                route_id=route.id,
                pandal_id=pandal.id,
                sequence=stop_data.sequence,
                distance_from_previous_meters=stop_data.distance_from_previous_meters,
                estimated_travel_minutes=stop_data.estimated_travel_minutes,
                optional=stop_data.optional,
                stop_notes=stop_data.stop_notes,
            )
            db.add(rs)

        if pandal_ids:
            route.start_pandal_id = pandal_ids[0]
            route.end_pandal_id = pandal_ids[-1]

        db.flush()
        imported_routes.append(route.slug)

    db.commit()
    return {"success": True, "imported_routes": imported_routes}
