# GeoGuess

A GeoGuessr-like web game built with React + TypeScript on the frontend and
FastAPI + SQLite on the backend, using free street imagery from
[Mapillary](https://www.mapillary.com/).

## Features

- **Demo mode** — 13 bundled equirectangular panoramas, **no API key needed**.
  Played through Pannellum (loaded from CDN). Perfect for trying the game on
  mobile or in environments without Mapillary access.
- **Classic mode** — 5 random panoramas anywhere in a chosen region, score by
  distance to the true location (GeoGuessr-style 0–5000 per round). Requires
  a free Mapillary token.
- **Region / country filters** — World, continents, and 12 specific countries.
- **Daily challenge** — same 5 panoramas for everyone, refreshed at UTC midnight.
- **Local leaderboard** — every game is saved in the browser's `localStorage`.
- **Online leaderboard** — sign up / log in to submit scores to a global list.
- **Multiplayer** — create a private room, share the 5-character code, and
  play live with friends over WebSockets. Each round broadcasts the same
  panorama and ends when everyone has guessed (or after the 60-second timer).
- **Built-in chat** in the multiplayer lobby and during games.
- **Mobile-responsive UI** — hamburger menu, panorama-on-top / map-on-bottom
  split, touch-friendly tap targets.

## Project layout

```
geo-guess-game/
├── backend/                # FastAPI app (Python 3.12, uv)
│   ├── main.py
│   └── app/
│       ├── auth.py         # JWT + bcrypt
│       ├── db.py           # SQLModel / SQLite
│       ├── mapillary.py    # Graph API client (server-side)
│       ├── regions.py      # bbox definitions per region
│       ├── scoring.py      # haversine + GeoGuessr-style decay
│       └── routers/
│           ├── auth.py         # POST /api/auth/{signup,login}, GET /me
│           ├── locations.py    # GET /api/locations/{regions,random}
│           ├── daily.py        # GET /api/daily/today
│           ├── scores.py       # POST /api/scores/submit, GET /api/scores/leaderboard
│           └── multiplayer.py  # POST /api/multiplayer/rooms + WS /ws/room/{code}
└── frontend/               # React 19 + Vite 8
    └── src/
        ├── pages/{Home,Game,Login,Leaderboard,Multiplayer,Room}.tsx
        ├── components/{Header,GuessMap,PanoramaView}.tsx
        ├── lib/{api,auth,scoring,local-leaderboard}.ts(x)
        ├── App.tsx
        └── main.tsx
```

## Prerequisites

- **Node.js ≥ 20** (Vite 8 requires 20.19+ ideally; 22.12 works with warnings)
- **Python 3.12** + [`uv`](https://docs.astral.sh/uv/) (or pip)
- (Optional) A free **Mapillary client token** for Classic / Daily / Multiplayer
  modes — register at https://www.mapillary.com/dashboard/developers and copy
  the token that starts with `MLY|`. **Demo mode works without this.**

## Setup

```bash
# Backend
cd backend
# Optional — only needed for Mapillary-powered modes:
export MAPILLARY_CLIENT_TOKEN='MLY|your-token-here'
# Optional but recommended for stable JWT signing across restarts:
export GEO_GAME_JWT_SECRET="$(openssl rand -hex 32)"
uv sync
uv run uvicorn main:app --reload --port 8000

# Frontend (in a second terminal)
cd frontend
npm install
npm run dev
```

If no `MAPILLARY_CLIENT_TOKEN` is set, the home page automatically routes
"Start Game" to `/demo` and offers Demo mode in the game-mode card grid.

The Vite dev server proxies `/api` and `/ws` to the FastAPI server on port
8000, so you only need to open http://localhost:5173.

## How it works

### Picking a panorama

The backend keeps a small table of region bounding boxes (`app/regions.py`).
For a given region we sample a random `(lng, lat)` inside the bbox, expand a
small search bbox around it, and ask the [Mapillary Graph
API](https://www.mapillary.com/developer) for nearby panoramic images. We retry
with a wider radius if the first pick has no imagery. The Mapillary token
**stays on the server** — the frontend reads it via `/api/config` so it never
ends up in committed source.

### Scoring

Distance is computed with the haversine formula. The score per round uses an
exponential decay (`5000 · exp(-d / 2000 km)`), giving 5000 for a perfect
guess, ~3000 for a 1000 km guess, and ~700 for a continent-scale miss.

### Daily challenge

`app/routers/daily.py` seeds Python's RNG with the current UTC date, fetches
five panoramas, and writes them to `.daily_cache/<YYYY-MM-DD>.json`. The same
five rounds are served to every player for the day.

### Multiplayer

`app/routers/multiplayer.py` keeps room state in memory and drives the game
loop in an `asyncio.Task`. Players join `/ws/room/{code}` over WebSockets;
the server fetches all panoramas up front, then for each round broadcasts a
`round` message, waits for all guesses (or the 60s timer), and broadcasts a
`round_result`. After the final round it sends a `final` message with the
totals.

## API reference (short)

| Method | Path | Notes |
| ------ | ---- | ----- |
| `GET`  | `/api/health` | `{ ok, mapillary_configured }` |
| `GET`  | `/api/config` | `{ mapillary_client_token }` (read by the frontend) |
| `GET`  | `/api/locations/regions` | List of supported regions |
| `GET`  | `/api/locations/random?region=world` | One random panorama in a region |
| `GET`  | `/api/daily/today` | Today's 5-round daily set |
| `POST` | `/api/auth/signup` / `login` | `{ token, username }` |
| `POST` | `/api/scores/submit` | Auth required |
| `GET`  | `/api/scores/leaderboard?region=...&mode=...` | Top 25–100 scores |
| `POST` | `/api/multiplayer/rooms` | Returns a 5-char room code |
| `WS`   | `/ws/room/{code}?username=...` | Lobby + game stream |

## Notes / limitations

- Multiplayer state lives in process memory, so a server restart drops rooms.
  Fine for dev / a single-instance deployment.
- The first round of a daily challenge can take a few seconds while Mapillary
  finds five panoramas; subsequent loads in the same UTC day hit the cache.
- Mapillary coverage isn't uniform — small countries with sparse imagery may
  occasionally fall back to non-panoramic photos.
