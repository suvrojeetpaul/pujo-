from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.admin import router as admin_router
from app.api.journeys import router as journeys_router
from app.api.routes import router as routes_router
from app.config import get_settings
from app.database import Base, engine, SessionLocal
from app import models  # noqa: F401 - registers SQLAlchemy models
from app.services.seed_service import seed_2026_routes

settings = get_settings()


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_2026_routes(db)
    finally:
        db.close()


initialize_database()


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="Pujo Path API",
    version="1.0.0",
    description="Curated Kolkata Durga Puja routes and sequential journeys.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(auth_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(routes_router, prefix="/api")
app.include_router(journeys_router, prefix="/api")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "pujo-path"}
