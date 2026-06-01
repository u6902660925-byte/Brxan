"""FastAPI entry point for the GeoGuessr-like game backend."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db
from app.routers import auth as auth_router
from app.routers import daily as daily_router
from app.routers import demo as demo_router
from app.routers import locations as locations_router
from app.routers import multiplayer as multiplayer_router
from app.routers import scores as scores_router


def create_app() -> FastAPI:
    app = FastAPI(title="GeoGuess", version="0.1.0")

    origins = os.environ.get("GEO_GAME_CORS", "*").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins if origins != ["*"] else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    init_db()

    app.include_router(auth_router.router)
    app.include_router(locations_router.router)
    app.include_router(daily_router.router)
    app.include_router(demo_router.router)
    app.include_router(scores_router.router)
    app.include_router(multiplayer_router.router)

    @app.get("/api/health")
    def health() -> dict:
        return {
            "ok": True,
            "mapillary_configured": bool(os.environ.get("MAPILLARY_CLIENT_TOKEN")),
        }

    @app.get("/api/config")
    def config() -> dict:
        token = os.environ.get("MAPILLARY_CLIENT_TOKEN", "")
        return {"mapillary_client_token": token}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
