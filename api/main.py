"""
Alpha Engine API — FastAPI backend.

Wraps the /src quant modules (backtester, analytics, strategies, data,
execution) into a REST + WebSocket API consumed by the Next.js terminal.

Run locally:
    uvicorn api.main:app --reload --port 8000
"""

import asyncio
import os
import sys
from typing import Any, Dict, List, Optional

# Project root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api.jobs import manager
from api.registry import public_schema
from api import services

app = FastAPI(
    title="Alpha Engine API",
    version="1.0.0",
    description="Quantitative research & backtesting API",
)

# CORS — allow the Vercel frontend + local dev. Override with env var.
_origins = os.getenv("CORS_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins.split(",")],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────── schemas ────────────────────────────

class CustomSpec(BaseModel):
    indicators: List[Dict[str, Any]] = []
    buy_query: str = ""
    sell_query: str = ""


class BacktestRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=20)
    start_date: str
    end_date: str
    strategy: str
    params: Dict[str, Any] = {}
    custom: Optional[CustomSpec] = None
    capital: float = 100000
    allocation: float = 0.95
    benchmark: str = "SPY"
    allow_short: bool = False
    use_stops: bool = False
    atr_multiplier: float = 2.0
    use_trailing_stop: bool = True
    use_circuit_breaker: bool = False
    circuit_breaker_pct: float = -0.03
    regime_gate: bool = False
    stress_test: bool = False
    mc_sims: int = 500


class CompareRequest(BaseModel):
    ticker: str
    start_date: str
    end_date: str
    capital: float = 100000
    allocation: float = 0.95


class OptimizeRequest(BaseModel):
    ticker: str
    start_date: str
    end_date: str
    strategy: str
    param_grid: Dict[str, List[Any]]
    metric: str = "sharpe_ratio"
    capital: float = 100000
    n_jobs: int = 1  # keep serial by default; small cloud instances choke on loky spawn


class WalkForwardRequest(BaseModel):
    ticker: str
    start_date: str
    end_date: str
    strategy: str
    params: Dict[str, Any] = {}
    n_splits: int = 5
    train_ratio: float = 0.7
    capital: float = 100000


# ──────────────────────────── meta ────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "alpha-engine-api"}


@app.get("/api/v1/strategies")
def strategies():
    return {"strategies": public_schema()}


@app.get("/api/v1/data/ohlcv")
def ohlcv(ticker: str, start: str, end: str):
    try:
        return services.get_ohlcv(ticker, start, end)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ──────────────────────────── jobs ────────────────────────────

@app.post("/api/v1/backtest/run")
def backtest_run(req: BacktestRequest):
    payload = req.model_dump()
    if payload.get("custom"):
        payload["custom"] = req.custom.model_dump()
    job_id = manager.submit("backtest", services.run_backtest_job, req=payload)
    return {"job_id": job_id}


@app.post("/api/v1/compare/run")
def compare_run(req: CompareRequest):
    job_id = manager.submit("compare", services.run_compare_job, req=req.model_dump())
    return {"job_id": job_id}


@app.post("/api/v1/optimize/run")
def optimize_run(req: OptimizeRequest):
    job_id = manager.submit("optimize", services.run_optimize_job, req=req.model_dump())
    return {"job_id": job_id}


@app.post("/api/v1/walkforward/run")
def walkforward_run(req: WalkForwardRequest):
    job_id = manager.submit(
        "walkforward", services.run_walkforward_job, req=req.model_dump()
    )
    return {"job_id": job_id}


@app.get("/api/v1/jobs/{job_id}")
def job_status(job_id: str, include_result: bool = True):
    job = manager.get(job_id, include_result=include_result)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.websocket("/ws/jobs/{job_id}")
async def job_progress_ws(ws: WebSocket, job_id: str):
    """Stream job progress. Sends final result when done."""
    await ws.accept()
    try:
        last = None
        while True:
            job = manager.get(job_id, include_result=False)
            if job is None:
                await ws.send_json({"error": "Job not found"})
                break
            snapshot = (job["status"], job["progress"], job["message"])
            if snapshot != last:
                await ws.send_json(job)
                last = snapshot
            if job["status"] in ("done", "error"):
                if job["status"] == "done":
                    full = manager.get(job_id, include_result=True)
                    await ws.send_json({"type": "result", "result": full["result"]})
                break
            await asyncio.sleep(0.4)
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await ws.close()
        except Exception:
            pass


# ──────────────────────────── live (Alpaca, read-only) ────────────────────────────

def _broker():
    key = os.getenv("ALPACA_API_KEY")
    secret = os.getenv("ALPACA_SECRET_KEY")
    if not key or not secret:
        raise HTTPException(
            status_code=503,
            detail="Alpaca keys not configured. Set ALPACA_API_KEY and ALPACA_SECRET_KEY.",
        )
    from src.execution.alpaca_broker import AlpacaBroker
    try:
        return AlpacaBroker(api_key=key, secret_key=secret)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Alpaca connection failed: {e}")


@app.get("/api/v1/live/account")
def live_account():
    return _broker().get_account_summary()


@app.get("/api/v1/live/positions")
def live_positions():
    return {"positions": _broker().get_positions()}
