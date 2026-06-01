"""Location pickup endpoints — find a Mapillary panorama for a region."""

from __future__ import annotations

import random

from fastapi import APIRouter, HTTPException

from ..mapillary import MapillaryError, find_pano_in_bbox
from ..regions import get_region, list_regions


router = APIRouter(prefix="/api/locations", tags=["locations"])


@router.get("/regions")
def regions() -> list[dict]:
    return list_regions()


@router.get("/random")
async def random_location(region: str = "world") -> dict:
    r = get_region(region)
    rng = random.Random()
    try:
        img = await find_pano_in_bbox(r.bbox, rng=rng)
    except MapillaryError as exc:
        raise HTTPException(502, str(exc))
    return {"image_id": img.id, "lat": img.lat, "lng": img.lng, "region": r.code}
