# Alpha Engine v2 — Deployment Guide

New architecture: the Python quant engine (`/src`) is now exposed through a
FastAPI backend (`/api`), consumed by a Next.js trading-terminal frontend
(`/frontend`). The old Streamlit app (`/app`) still works and is untouched.

```
┌─────────────────────┐         ┌──────────────────────────┐
│  Next.js Terminal   │  HTTPS  │  FastAPI (api/main.py)   │
│  frontend/ → Vercel │ ──────▶ │  Dockerfile.api → Render │
│  TradingView charts │  WS/REST│  wraps src/* modules     │
└─────────────────────┘         └──────────────────────────┘
```

## 1. Backend → Render

1. Push this repo to GitHub.
2. Render → New → Web Service → connect the repo.
3. Environment: **Docker**, and set **Dockerfile Path** = `Dockerfile.api`.
4. Environment variables (optional):
   - `CORS_ORIGINS` = `https://your-app.vercel.app` (comma-separated; default `*`)
   - `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` = paper trading keys (enables the LIVE tab)
5. Deploy. Verify: `https://your-api.onrender.com/health` → `{"status":"ok"}`

Note: your existing Streamlit service keeps using `Dockerfile` — the two can
run side by side as separate Render services.

## 2. Frontend → Vercel

1. Vercel → New Project → import the same repo.
2. **Root Directory** = `frontend`   (important!)
3. Environment variable:
   - `NEXT_PUBLIC_API_URL` = `https://your-api.onrender.com`
4. Deploy.

## 3. Local development

```bash
# Terminal 1 — API
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm install
cp .env.local.example .env.local   # points at http://localhost:8000
npm run dev                        # http://localhost:3000
```

## API surface

| Endpoint | Purpose |
|---|---|
| `GET /health` | Liveness check |
| `GET /api/v1/strategies` | Strategy registry + param schemas |
| `GET /api/v1/data/ohlcv` | Raw OHLCV candles |
| `POST /api/v1/backtest/run` | Full backtest job (metrics, equity, MC, regimes…) |
| `POST /api/v1/compare/run` | All strategies side-by-side |
| `POST /api/v1/optimize/run` | Grid-search + sensitivity heatmap |
| `POST /api/v1/walkforward/run` | Rolling out-of-sample validation |
| `GET /api/v1/jobs/{id}` | Poll job status/result |
| `WS /ws/jobs/{id}` | Stream job progress |
| `GET /api/v1/live/account` | Alpaca account (read-only) |
| `GET /api/v1/live/positions` | Alpaca open positions (read-only) |

Heavy work runs in an in-process job queue (`api/jobs.py`) — no Redis/Celery
needed on a single instance. Progress streams over WebSocket with automatic
REST-polling fallback (Render free tier friendly).

## Free-tier reality check

- Render free spins the API down after idle; first request takes ~30–60 s to
  wake. The frontend shows a hint when this happens. `cron-job.org` pinging
  `/health` every 10 min keeps it warm.
- Vercel static frontend never sleeps — the UI loads instantly even while the
  API wakes up.
