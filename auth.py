"""Account signup + login endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session

from ..auth import (
    current_user,
    get_user_by_username,
    hash_password,
    make_token,
    verify_password,
)
from ..db import User, get_session


router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthRequest(BaseModel):
    username: str = Field(min_length=2, max_length=32)
    password: str = Field(min_length=4, max_length=128)


class AuthResponse(BaseModel):
    token: str
    username: str


class MeResponse(BaseModel):
    id: int
    username: str


def _session() -> Session:
    with get_session() as s:
        yield s


@router.post("/signup", response_model=AuthResponse)
def signup(req: AuthRequest, session: Session = Depends(_session)) -> AuthResponse:
    if get_user_by_username(session, req.username):
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already taken")
    user = User(username=req.username, password_hash=hash_password(req.password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return AuthResponse(token=make_token(user), username=user.username)


@router.post("/login", response_model=AuthResponse)
def login(req: AuthRequest, session: Session = Depends(_session)) -> AuthResponse:
    user = get_user_by_username(session, req.username)
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return AuthResponse(token=make_token(user), username=user.username)


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(current_user)) -> MeResponse:
    return MeResponse(id=user.id or 0, username=user.username)
