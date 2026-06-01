"""Score submission + leaderboard endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, desc, select

from ..auth import current_user
from ..db import Score, User, get_session


router = APIRouter(prefix="/api/scores", tags=["scores"])


class SubmitScore(BaseModel):
    region: str = Field(default="world")
    mode: str = Field(default="classic")  # "classic" | "daily"
    daily_key: Optional[str] = None
    total_score: int = Field(ge=0, le=25_000)
    rounds_played: int = Field(ge=1, le=10)


class LeaderboardEntry(BaseModel):
    username: str
    total_score: int
    region: str
    mode: str
    daily_key: Optional[str]
    created_at: datetime


def _session() -> Session:
    with get_session() as s:
        yield s


@router.post("/submit", response_model=LeaderboardEntry)
def submit_score(
    body: SubmitScore,
    user: User = Depends(current_user),
    session: Session = Depends(_session),
) -> LeaderboardEntry:
    score = Score(
        user_id=user.id or 0,
        username=user.username,
        region=body.region,
        mode=body.mode,
        daily_key=body.daily_key,
        total_score=body.total_score,
        rounds_played=body.rounds_played,
    )
    session.add(score)
    session.commit()
    session.refresh(score)
    return LeaderboardEntry(
        username=score.username,
        total_score=score.total_score,
        region=score.region,
        mode=score.mode,
        daily_key=score.daily_key,
        created_at=score.created_at,
    )


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
def leaderboard(
    region: Optional[str] = Query(default=None),
    mode: Optional[str] = Query(default=None),
    daily_key: Optional[str] = Query(default=None),
    limit: int = Query(default=25, le=100),
    session: Session = Depends(_session),
) -> list[LeaderboardEntry]:
    stmt = select(Score)
    if region:
        stmt = stmt.where(Score.region == region)
    if mode:
        stmt = stmt.where(Score.mode == mode)
    if daily_key:
        stmt = stmt.where(Score.daily_key == daily_key)
    stmt = stmt.order_by(desc(Score.total_score)).limit(limit)
    rows = session.exec(stmt).all()
    return [
        LeaderboardEntry(
            username=r.username,
            total_score=r.total_score,
            region=r.region,
            mode=r.mode,
            daily_key=r.daily_key,
            created_at=r.created_at,
        )
        for r in rows
    ]
