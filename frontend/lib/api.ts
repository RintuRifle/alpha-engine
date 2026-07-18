/** API client + types for the Alpha Engine FastAPI backend. */

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

// ── Types ──────────────────────────────────────────────────────────

export interface ParamSchema {
  name: string;
  label: string;
  type: "int" | "float";
  default: number;
  min: number;
  max: number;
  step: number;
}

export interface StrategySchema {
  key: string;
  label: string;
  description: string;
  params: ParamSchema[];
}

export interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number | null;
}

export interface Trade {
  time: string;
  action: "BUY" | "SELL" | "SHORT" | "COVER";
  quantity: number;
  price: number;
  commission: number;
  slippage: number;
}

export interface EquityPoint {
  time: string;
  equity: number;
  drawdown: number;
}

export interface BacktestResult {
  ticker: string;
  strategy_key: string;
  strategy_label: string;
  strategy_name: string;
  params: Record<string, number>;
  start_date: string;
  end_date: string;
  metrics: Record<string, number | null>;
  candles: Candle[];
  trades: Trade[];
  equity: EquityPoint[];
  benchmark: { time: string; equity: number }[] | null;
  monthly_returns: {
    years: number[];
    data: (number | null)[][];
    yearly: (number | null)[];
  };
  rolling: {
    time: string;
    sharpe: number | null;
    sortino: number | null;
    volatility: number | null;
  }[];
  returns_hist: {
    bins: number[];
    counts: number[];
    mean?: number;
    std?: number;
    skew?: number;
    kurtosis?: number;
  };
  monte_carlo: {
    p05: number[];
    p25: number[];
    p50: number[];
    p75: number[];
    p95: number[];
    stats: Record<string, number>;
    stress?: Record<string, unknown>[];
  } | null;
  regimes: { time: string; regime: string }[];
  warning: string | null;
}

export interface CompareResult {
  ticker: string;
  capital: number;
  results: {
    key: string;
    label: string;
    metrics?: Record<string, number | null>;
    final_equity?: number;
    equity?: EquityPoint[];
    error?: string;
  }[];
}

export interface OptimizeResult {
  ticker: string;
  strategy_label: string;
  metric: string;
  best_params: Record<string, number>;
  best_value: number | null;
  total_combinations: number;
  elapsed_seconds?: number;
  top_results: {
    params: Record<string, number>;
    value: number | null;
    cagr: number | null;
    max_drawdown: number | null;
  }[];
  heatmap: {
    x_param: string;
    y_param: string;
    x_values: number[];
    y_values: number[];
    z_values: (number | null)[][];
  } | null;
}

export interface WalkForwardResult {
  ticker: string;
  strategy_label: string;
  windows: {
    window: number;
    train_size: number;
    test_size: number;
    test_return: number | null;
    num_trades: number;
    error?: string | null;
  }[];
  summary: {
    avg_return: number | null;
    consistency: number | null;
    n_windows: number;
  };
}

export interface JobState {
  id: string;
  kind: string;
  status: "queued" | "running" | "done" | "error";
  progress: number;
  message: string;
  error: string | null;
  result?: unknown;
}

export interface BacktestConfig {
  ticker: string;
  start_date: string;
  end_date: string;
  strategy: string;
  params: Record<string, number>;
  custom?: {
    indicators: Record<string, unknown>[];
    buy_query: string;
    sell_query: string;
  };
  capital: number;
  allocation: number;
  benchmark: string;
  allow_short: boolean;
  use_stops: boolean;
  atr_multiplier: number;
  use_trailing_stop: boolean;
  use_circuit_breaker: boolean;
  regime_gate: boolean;
  stress_test: boolean;
}

// ── Client ─────────────────────────────────────────────────────────

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail || `${res.status} ${res.statusText}`);
  }
  return res.json();
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`);
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail || `${res.status} ${res.statusText}`);
  }
  return res.json();
}

export const api = {
  health: () => get<{ status: string }>("/health"),
  strategies: () => get<{ strategies: StrategySchema[] }>("/api/v1/strategies"),
  runBacktest: (cfg: BacktestConfig) =>
    post<{ job_id: string }>("/api/v1/backtest/run", cfg),
  runCompare: (cfg: {
    ticker: string;
    start_date: string;
    end_date: string;
    capital: number;
  }) => post<{ job_id: string }>("/api/v1/compare/run", cfg),
  runOptimize: (cfg: {
    ticker: string;
    start_date: string;
    end_date: string;
    strategy: string;
    param_grid: Record<string, number[]>;
    metric: string;
    capital: number;
  }) => post<{ job_id: string }>("/api/v1/optimize/run", cfg),
  runWalkForward: (cfg: {
    ticker: string;
    start_date: string;
    end_date: string;
    strategy: string;
    params: Record<string, number>;
    n_splits: number;
    capital: number;
  }) => post<{ job_id: string }>("/api/v1/walkforward/run", cfg),
  job: (id: string) => get<JobState>(`/api/v1/jobs/${id}`),
  liveAccount: () => get<Record<string, number | string>>("/api/v1/live/account"),
  livePositions: () =>
    get<{ positions: Record<string, number | string>[] }>(
      "/api/v1/live/positions"
    ),
};

/**
 * Track a job to completion. Tries WebSocket streaming first,
 * falls back to REST polling.
 */
export function trackJob<T>(
  jobId: string,
  onProgress: (pct: number, msg: string) => void
): Promise<T> {
  return new Promise((resolve, reject) => {
    let settled = false;

    const poll = async () => {
      while (!settled) {
        try {
          const j = await api.job(jobId);
          onProgress(j.progress, j.message);
          if (j.status === "done") {
            settled = true;
            resolve(j.result as T);
            return;
          }
          if (j.status === "error") {
            settled = true;
            reject(new Error(j.message || "Job failed"));
            return;
          }
        } catch (e) {
          settled = true;
          reject(e);
          return;
        }
        await new Promise((r) => setTimeout(r, 900));
      }
    };

    try {
      const wsUrl = API_URL.replace(/^http/, "ws") + `/ws/jobs/${jobId}`;
      const ws = new WebSocket(wsUrl);
      const wsTimeout = setTimeout(() => {
        try { ws.close(); } catch {}
        if (!settled) poll();
      }, 3000);

      ws.onopen = () => clearTimeout(wsTimeout);
      ws.onmessage = (ev) => {
        const data = JSON.parse(ev.data);
        if (data.type === "result") {
          settled = true;
          resolve(data.result as T);
          ws.close();
        } else if (data.status === "error") {
          settled = true;
          reject(new Error(data.message || "Job failed"));
          ws.close();
        } else if (data.status) {
          onProgress(data.progress ?? 0, data.message ?? "");
        }
      };
      ws.onerror = () => {
        clearTimeout(wsTimeout);
        try { ws.close(); } catch {}
        if (!settled) poll();
      };
      ws.onclose = () => {
        // If closed without result (e.g. proxy killed WS), fall back to polling
        if (!settled) poll();
      };
    } catch {
      poll();
    }
  });
}
