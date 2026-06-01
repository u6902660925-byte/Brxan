"""Daily challenge — a deterministic 5-round set, identical for every player.

We seed Python's RNG with the UTC date so all calls in the same day yield the
same five panoramas. Mapillary results aren't deterministic by themselves, so
we cache the result for the day in-memory; restarting the server inside the
same UTC day reuses the cache file on disk.
"""

from __future__ import annotations

import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..mapillary import MapillaryError, find_pano_in_bbox
from ..regions import get_region


router = APIRouter(prefix="/api/daily", tags=["daily"])


CACHE_DIR = Path(os.environ.get("GEO_GAME_DAILY_CACHE", ".daily_cache"))
CACHE_DIR.mkdir(exist_ok=True)


def today_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _seed_for(day: str) -> int:
    return int.from_bytes(day.encode(), "big") % (2**31)


@router.get("/today")
async def daily_today() -> dict:
    day = today_key()
    cache_path = CACHE_DIR / f"{day}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text())

    rng = random.Random(_seed_for(day))
    region = get_region("world")
    rounds: list[dict] = []
    try:
        for _ in range(5):
            img = await find_pano_in_bbox(region.bbox, rng=rng)
            rounds.append({"image_id": img.id, "lat": img.lat, "lng": img.lng})
    except MapillaryError as exc:
        raise HTTPException(502, str(exc))

    payload = {"daily_key": day, "rounds": rounds}
    cache_path.write_text(json.dumps(payload))
    return payload
