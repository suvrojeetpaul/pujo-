from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, new_uuid
from app.schemas import GuestSessionResponse, LoginRequest, RegisterRequest, TokenResponse
from app.services.auth import (
    create_access_token,
    create_guest_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/guest", response_model=GuestSessionResponse)
def create_guest_session() -> GuestSessionResponse:
    guest_session_id = new_uuid()
    return GuestSessionResponse(
        guest_session_id=guest_session_id,
        token=create_guest_token(guest_session_id),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email is already registered")
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _tokens_for(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.is_active or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return _tokens_for(user)


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return {"id": user.id, "email": user.email, "full_name": user.full_name, "is_admin": user.is_admin}


def _tokens_for(user: User) -> TokenResponse:
    claims = {"sub": user.id}
    return TokenResponse(
        access_token=create_access_token(claims),
        refresh_token=create_refresh_token(claims),
        user_id=user.id,
        is_admin=user.is_admin,
    )
