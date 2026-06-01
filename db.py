"""SQLite database setup using SQLModel."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel, Session, create_engine


DB_PATH = os.environ.get("GEO_GAME_DB", "geo_game.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"
_engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str
    created_at: datetime = Field(default_factory=utcnow)


class Score(SQLModel, table=True):
    """A finished game submitted by a player."""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    username: str = Field(index=True)
    region: str = Field(index=True)
    mode: str = Field(index=True)  # "classic" | "daily"
    daily_key: Optional[str] = Field(default=None, index=True)
    total_score: int
    rounds_played: int
    created_at: datetime = Field(default_factory=utcnow, index=True)


def init_db() -> None:
    SQLModel.metadata.create_all(_engine)


def get_session() -> Session:
    return Session(_engine)
