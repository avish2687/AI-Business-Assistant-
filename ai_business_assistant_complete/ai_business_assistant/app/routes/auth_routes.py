from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from datetime import timedelta

from app.db.base import get_db
from app.db.models import User, ContentHistory
from app.services.auth_service import (
    create_user, authenticate_user, create_access_token,
    get_current_active_user
)
from app.core.config import settings

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field("", max_length=100)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: str
    email: str
    full_name: str | None
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/register", response_model=UserOut, status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user."""
    user = create_user(db, req.email, req.password, req.full_name)
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "created_at": str(user.created_at),
    }


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login and receive a JWT access token."""
    user = authenticate_user(db, form_data.username, form_data.password)
    token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
def get_profile(current_user: User = Depends(get_current_active_user)):
    """Get current user's profile."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "created_at": str(current_user.created_at),
    }


@router.get("/history")
def get_history(
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's content generation history."""
    history = (
        db.query(ContentHistory)
        .filter(ContentHistory.user_id == current_user.id)
        .order_by(ContentHistory.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": h.id,
            "content_type": h.content_type,
            "input_data": h.input_data,
            "output_preview": h.output_data[:200] + "..." if len(h.output_data) > 200 else h.output_data,
            "created_at": str(h.created_at),
        }
        for h in history
    ]
