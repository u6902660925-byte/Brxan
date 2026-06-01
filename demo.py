"""Endpoints that expose the bundled demo panoramas (no Mapillary token needed)."""

from __future__ import annotations

import random

import httpx
from fastapi import APIRouter, HTTPException, Response

from ..demo_panos import PANORAMAS, get_demo_pano


router = APIRouter(prefix="/api/demo", tags=["demo"])

_USER_AGENT = "GeoGuess/0.1 (https://github.com/cognition-ai/geoguess; demo mode panoramas)"


def _proxied_url(pano_id: str) -> str:
    return f"/api/demo/image/{pano_id}"


def _list_for_client() -> list[dict]:
    return [
        {
            "id": p.id,
            "name": p.name,
            "url": _proxied_url(p.id),
            "lat": p.lat,
            "lng": p.lng,
        }
        for p in PANORAMAS
    ]


@router.get("/panos")
def panos() -> list[dict]:
    return _list_for_client()


@router.get("/random")
def random_pano(seed: int | None = None) -> dict:
    if not PANORAMAS:
        raise HTTPException(503, "No demo panoramas configured")
    rng = random.Random(seed) if seed is not None else random.Random()
    p = rng.choice(PANORAMAS)
    return {
        "id": p.id,
        "name": p.name,
        "url": _proxied_url(p.id),
        "lat": p.lat,
        "lng": p.lng,
    }


@router.get("/image/{pano_id}")
async def image(pano_id: str) -> Response:
    """Proxy image bytes so the browser sees them as same-origin (no CORS issues)."""
    pano = get_demo_pano(pano_id)
    if not pano:
        raise HTTPException(404, "Unknown panorama")
    async with httpx.AsyncClient(
        timeout=20.0, follow_redirects=True, headers={"User-Agent": _USER_AGENT}
    ) as client:
        try:
            r = await client.get(pano.url)
            r.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(502, f"Upstream image fetch failed: {exc}") from exc
    return Response(
        content=r.content,
        media_type=r.headers.get("content-type", "image/jpeg"),
        headers={"Cache-Control": "public, max-age=86400"},
    )
