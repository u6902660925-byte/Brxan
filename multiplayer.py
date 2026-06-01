"""Multiplayer rooms over WebSockets.

Flow:

1. ``POST /api/multiplayer/rooms`` creates a room (host only) with chosen
   region + round count, returning a short room code.
2. Players (logged in or guests) connect to ``/ws/room/{code}?username=...``.
3. The host sends ``{"type": "start"}``. The server fetches N panoramas from
   Mapillary up-front and broadcasts each round to all players.
4. Players send ``{"type": "guess", "lat": ..., "lng": ...}``. When everyone
   has guessed (or the timer expires) the server broadcasts the round result.
5. After the final round the server broadcasts ``{"type": "final"}`` with the
   per-player totals so the client can show the scoreboard.

Game state lives in-process which is fine for a single-instance dev server.
"""

from __future__ import annotations

import asyncio
import json
import random
import secrets
import string
from dataclasses import dataclass, field
from typing import Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from ..mapillary import MapillaryError, find_pano_in_bbox
from ..regions import get_region
from ..scoring import haversine_km, score_for_distance


router = APIRouter(tags=["multiplayer"])

ROUND_TIMEOUT_SECONDS = 60.0


@dataclass
class Player:
    username: str
    websocket: WebSocket
    is_host: bool = False
    total_score: int = 0
    last_guess: Optional[tuple[float, float]] = None
    last_distance_km: Optional[float] = None
    last_round_score: Optional[int] = None


@dataclass
class RoundData:
    image_id: str
    lat: float
    lng: float


@dataclass
class Room:
    code: str
    region: str
    rounds_count: int
    host_username: str
    players: dict[str, Player] = field(default_factory=dict)
    rounds: list[RoundData] = field(default_factory=list)
    current_round: int = -1  # -1 means lobby
    started: bool = False
    finished: bool = False
    round_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    round_event: asyncio.Event = field(default_factory=asyncio.Event)

    async def broadcast(self, message: dict) -> None:
        text = json.dumps(message)
        dead: list[str] = []
        for username, p in list(self.players.items()):
            try:
                await p.websocket.send_text(text)
            except Exception:
                dead.append(username)
        for u in dead:
            self.players.pop(u, None)

    def lobby_state(self) -> dict:
        return {
            "type": "lobby",
            "code": self.code,
            "region": self.region,
            "rounds_count": self.rounds_count,
            "host": self.host_username,
            "started": self.started,
            "players": [
                {"username": p.username, "is_host": p.is_host}
                for p in self.players.values()
            ],
        }


_rooms: dict[str, Room] = {}


def _new_code() -> str:
    return "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(5))


class CreateRoom(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    region: str = "world"
    rounds_count: int = Field(default=5, ge=1, le=10)


class CreateRoomResponse(BaseModel):
    code: str


@router.post("/api/multiplayer/rooms", response_model=CreateRoomResponse)
def create_room(body: CreateRoom) -> CreateRoomResponse:
    for _ in range(20):
        code = _new_code()
        if code not in _rooms:
            break
    else:
        raise HTTPException(503, "Could not allocate a room code")
    _rooms[code] = Room(
        code=code,
        region=body.region,
        rounds_count=body.rounds_count,
        host_username=body.username,
    )
    return CreateRoomResponse(code=code)


@router.get("/api/multiplayer/rooms/{code}")
def get_room(code: str) -> dict:
    room = _rooms.get(code.upper())
    if not room:
        raise HTTPException(404, "Room not found")
    return room.lobby_state()


@router.websocket("/ws/room/{code}")
async def room_socket(websocket: WebSocket, code: str, username: str) -> None:
    code = code.upper()
    await websocket.accept()
    room = _rooms.get(code)
    if not room:
        await websocket.send_text(json.dumps({"type": "error", "message": "Room not found"}))
        await websocket.close()
        return

    # Ensure unique username inside the room.
    base = username.strip() or "Player"
    name = base
    i = 2
    while name in room.players:
        name = f"{base}{i}"
        i += 1

    is_host = (name == room.host_username) or (not room.players and not room.started)
    if is_host:
        room.host_username = name

    player = Player(username=name, websocket=websocket, is_host=is_host)
    room.players[name] = player

    await room.broadcast(room.lobby_state())
    if room.started and not room.finished and 0 <= room.current_round < len(room.rounds):
        # Late join — send the current round so they can play along.
        rd = room.rounds[room.current_round]
        await websocket.send_text(
            json.dumps(
                {
                    "type": "round",
                    "round": room.current_round + 1,
                    "rounds_total": room.rounds_count,
                    "image_id": rd.image_id,
                }
            )
        )

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            mtype = msg.get("type")

            if mtype == "start" and player.is_host and not room.started:
                asyncio.create_task(_run_game(room))

            elif mtype == "guess" and room.started and not room.finished:
                lat = msg.get("lat")
                lng = msg.get("lng")
                if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
                    continue
                player.last_guess = (float(lat), float(lng))
                if all(p.last_guess is not None for p in room.players.values()):
                    room.round_event.set()

            elif mtype == "chat":
                text = str(msg.get("message") or "")[:200]
                await room.broadcast(
                    {"type": "chat", "from": player.username, "message": text}
                )

    except WebSocketDisconnect:
        pass
    finally:
        room.players.pop(name, None)
        if room.players:
            await room.broadcast(room.lobby_state())
        elif room.finished:
            # Game over and nobody left — clean up immediately.
            _rooms.pop(code, None)
        else:
            # Briefly hold the room open so React StrictMode / quick reloads
            # don't accidentally delete a room before the new socket arrives.
            asyncio.create_task(_cleanup_idle_room(code))


async def _cleanup_idle_room(code: str, delay: float = 30.0) -> None:
    await asyncio.sleep(delay)
    room = _rooms.get(code)
    if room and not room.players:
        _rooms.pop(code, None)


async def _run_game(room: Room) -> None:
    """Drive a full game for the given room."""
    if room.started:
        return
    room.started = True

    rng = random.Random()
    region = get_region(room.region)

    try:
        rounds: list[RoundData] = []
        for _ in range(room.rounds_count):
            img = await find_pano_in_bbox(region.bbox, rng=rng)
            rounds.append(RoundData(image_id=img.id, lat=img.lat, lng=img.lng))
        room.rounds = rounds
    except MapillaryError as exc:
        await room.broadcast({"type": "error", "message": str(exc)})
        room.started = False
        return

    await room.broadcast(
        {"type": "game_start", "rounds_count": room.rounds_count, "region": room.region}
    )

    for idx, rd in enumerate(rounds):
        room.current_round = idx
        room.round_event = asyncio.Event()
        for p in room.players.values():
            p.last_guess = None
            p.last_distance_km = None
            p.last_round_score = None

        await room.broadcast(
            {
                "type": "round",
                "round": idx + 1,
                "rounds_total": room.rounds_count,
                "image_id": rd.image_id,
                "timeout": ROUND_TIMEOUT_SECONDS,
            }
        )

        try:
            await asyncio.wait_for(room.round_event.wait(), timeout=ROUND_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            pass

        for p in room.players.values():
            if p.last_guess is None:
                p.last_distance_km = None
                p.last_round_score = 0
            else:
                d = haversine_km(rd.lat, rd.lng, p.last_guess[0], p.last_guess[1])
                p.last_distance_km = d
                p.last_round_score = score_for_distance(d)
                p.total_score += p.last_round_score

        await room.broadcast(
            {
                "type": "round_result",
                "round": idx + 1,
                "true_lat": rd.lat,
                "true_lng": rd.lng,
                "results": [
                    {
                        "username": p.username,
                        "guess_lat": p.last_guess[0] if p.last_guess else None,
                        "guess_lng": p.last_guess[1] if p.last_guess else None,
                        "distance_km": p.last_distance_km,
                        "round_score": p.last_round_score,
                        "total_score": p.total_score,
                    }
                    for p in room.players.values()
                ],
            }
        )
        await asyncio.sleep(4)

    room.finished = True
    await room.broadcast(
        {
            "type": "final",
            "results": sorted(
                [
                    {"username": p.username, "total_score": p.total_score}
                    for p in room.players.values()
                ],
                key=lambda r: r["total_score"],
                reverse=True,
            ),
        }
    )
