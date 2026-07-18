"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  api,
  trackJob,
  type StrategySchema,
  type BacktestResult,
  type CompareResult,
} from "@/lib/api";
import { isoDaysAgo, todayIso } from "@/lib/format";
import { TopBar } from "@/components/TopBar";
import {
  ConfigPanel,
  toBacktestRequest,
  type ConfigState,
} from "@/components/ConfigPanel";
import { DEFAULT_CUSTOM } from "@/components/CustomBuilder";
import { Panel } from "@/components/Panel";
import { MetricCards } from "@/components/MetricCards";
import { PriceChart } from "@/components/PriceChart";
import {
  EquityChart,
  DrawdownChart,
  RollingChart,
} from "@/components/EquityChart";
import { MonthlyHeatmap } from "@/components/MonthlyHeatmap";
import { HistChart } from "@/components/HistChart";
import { MonteCarloView } from "@/components/MonteCarloView";
import { WalkForwardView } from "@/components/WalkForwardView";
import { OptimizerView } from "@/components/OptimizerView";
import { CompareView } from "@/components/CompareView";
import { TradesTable } from "@/components/TradesTable";
import { LivePanel } from "@/components/LivePanel";

const TABS = [
  "OVERVIEW",
  "PRICE ACTION",
  "ANALYTICS",
  "MONTE CARLO",
  "WALK-FORWARD",
  "OPTIMIZER",
  "COMPARE",
  "TRADES",
  "LIVE",
] as const;
type Tab = (typeof TABS)[number];

const DEFAULT_CONFIG: ConfigState = {
  ticker: "AAPL",
  start_date: isoDaysAgo(365 * 3),
  end_date: todayIso(),
  interval: "1d",
  intraday_square_off: false,
  capital: 100000,
  allocation: 0.95,
  benchmark: "SPY",
  strategy: "sma_crossover",
  params: { short_window: 50, long_window: 200 },
  custom: DEFAULT_CUSTOM,
  allow_short: false,
  use_stops: false,
  atr_multiplier: 2.0,
  use_trailing_stop: true,
  use_circuit_breaker: false,
  regime_gate: false,
  stress_test: false,
};

export default function Terminal() {
  const [strategies, setStrategies] = useState<StrategySchema[]>([]);
  const [config, setConfig] = useState<ConfigState>(DEFAULT_CONFIG);
  const [tab, setTab] = useState<Tab>("OVERVIEW");
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState({ pct: 0, msg: "" });
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [compare, setCompare] = useState<CompareResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .strategies()
      .then((r) => setStrategies(r.strategies))
      .catch(() =>
        setError(
          "Cannot reach the API. If the backend is on Render free tier, it may be waking up — retry in ~30s."
        )
      );
  }, []);

  const runBacktest = async () => {
    setRunning(true);
    setError(null);
    setProgress({ pct: 0, msg: "Submitting..." });
    try {
      const { job_id } = await api.runBacktest(toBacktestRequest(config));
      const res = await trackJob<BacktestResult>(job_id, (pct, msg) =>
        setProgress({ pct, msg })
      );
      setResult(res);
      if (tab === "COMPARE" || tab === "LIVE") setTab("OVERVIEW");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  };

  const runCompare = async () => {
    setRunning(true);
    setError(null);
    setProgress({ pct: 0, msg: "Submitting..." });
    setTab("COMPARE");
    try {
      const { job_id } = await api.runCompare({
        ticker: config.ticker,
        start_date: config.start_date,
        end_date: config.end_date,
        interval: config.interval,
        capital: config.capital,
      });
      setCompare(
        await trackJob<CompareResult>(job_id, (pct, msg) =>
          setProgress({ pct, msg })
        )
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  };

  const stratLabel =
    strategies.find((s) => s.key === config.strategy)?.label ?? "—";

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <TopBar ticker={config.ticker} strategyLabel={stratLabel} />

      {/* progress rail */}
      <div className="h-0.5 bg-line relative shrink-0">
        {running && (
          <motion.div
            className="absolute inset-y-0 left-0 bg-amber shadow-[0_0_8px_#f7a600]"
            animate={{ width: `${Math.max(4, progress.pct)}%` }}
            transition={{ ease: "easeOut" }}
          />
        )}
      </div>

      <div className="flex flex-1 min-h-0">
        <ConfigPanel
          strategies={strategies}
          config={config}
          setConfig={(u) => setConfig(u)}
          running={running}
          onRun={runBacktest}
          onCompare={runCompare}
        />

        <main className="flex-1 min-w-0 flex flex-col">
          {/* tab bar */}
          <nav className="flex border-b border-line bg-panel overflow-x-auto shrink-0">
            {TABS.map((t) => (
              <button
                key={t}
                className={`tab-btn ${tab === t ? "active" : ""}`}
                onClick={() => setTab(t)}
              >
                {t}
              </button>
            ))}
            {running && (
              <span className="ml-auto self-center px-3 text-xxs text-amber whitespace-nowrap animate-pulse">
                {progress.pct}% — {progress.msg}
              </span>
            )}
          </nav>

          <div className="flex-1 overflow-y-auto p-3">
            {error && (
              <div className="border border-down/50 bg-down/10 rounded-sm px-3 py-2 mb-3 text-xxs text-down">
                {error}
              </div>
            )}
            {result?.warning && tab === "OVERVIEW" && (
              <div className="border border-amber/50 bg-amber/10 rounded-sm px-3 py-2 mb-3 text-xxs text-amber">
                {result.warning}
              </div>
            )}

            <AnimatePresence mode="wait">
              <motion.div
                key={tab}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.18 }}
              >
                {tab === "OVERVIEW" &&
                  (result ? (
                    <div className="space-y-3">
                      <div className="flex items-baseline justify-between flex-wrap gap-2">
                        <h2 className="text-sm font-semibold">
                          <span className="text-amber">{result.ticker}</span>
                          <span className="text-dim mx-2">·</span>
                          {result.strategy_name}
                          <span className="text-dim mx-2">·</span>
                          <span className="text-muted text-xxs">
                            {result.start_date} → {result.end_date}
                          </span>
                        </h2>
                      </div>
                      <MetricCards metrics={result.metrics} />
                      <Panel title="Equity Curve vs Benchmark" delay={0.05}>
                        <EquityChart result={result} />
                      </Panel>
                      <Panel title="Monthly Returns %" delay={0.1}>
                        <MonthlyHeatmap monthly={result.monthly_returns} />
                      </Panel>
                    </div>
                  ) : (
                    <EmptyState running={running} progress={progress} />
                  ))}

                {tab === "PRICE ACTION" &&
                  (result ? (
                    <Panel
                      title={`${result.ticker} — OHLCV + Executions (${result.trades.length} fills)`}
                    >
                      <PriceChart result={result} />
                    </Panel>
                  ) : (
                    <EmptyState running={running} progress={progress} />
                  ))}

                {tab === "ANALYTICS" &&
                  (result ? (
                    <div className="space-y-3">
                      <Panel title="Underwater Curve (drawdown)">
                        <DrawdownChart result={result} />
                      </Panel>
                      <Panel title="Rolling Risk-Adjusted Returns" delay={0.05}>
                        <RollingChart result={result} />
                      </Panel>
                      <Panel title="Daily Return Distribution" delay={0.1}>
                        <HistChart hist={result.returns_hist} />
                      </Panel>
                    </div>
                  ) : (
                    <EmptyState running={running} progress={progress} />
                  ))}

                {tab === "MONTE CARLO" &&
                  (result ? (
                    <MonteCarloView result={result} />
                  ) : (
                    <EmptyState running={running} progress={progress} />
                  ))}

                {tab === "WALK-FORWARD" && <WalkForwardView config={config} />}

                {tab === "OPTIMIZER" && (
                  <OptimizerView config={config} strategies={strategies} />
                )}

                {tab === "COMPARE" && <CompareView result={compare} />}

                {tab === "TRADES" &&
                  (result ? (
                    <TradesTable result={result} />
                  ) : (
                    <EmptyState running={running} progress={progress} />
                  ))}

                {tab === "LIVE" && <LivePanel />}
              </motion.div>
            </AnimatePresence>
          </div>
        </main>
      </div>
    </div>
  );
}

function EmptyState({
  running,
  progress,
}: {
  running: boolean;
  progress: { pct: number; msg: string };
}) {
  if (running)
    return (
      <div className="space-y-3">
        <div className="skeleton h-20 rounded-sm" />
        <div className="skeleton h-72 rounded-sm" />
        <p className="text-xxs text-amber animate-pulse">
          {progress.pct}% — {progress.msg}
        </p>
      </div>
    );
  return (
    <div className="h-[60vh] flex flex-col items-center justify-center select-none">
      <pre className="text-dim text-micro leading-tight mb-4">{`
  ┌─────────────────────────────┐
  │  NO POSITION · NO SIGNAL    │
  │  AWAITING OPERATOR INPUT_   │
  └─────────────────────────────┘`}</pre>
      <p className="text-xxs text-muted">
        Configure an instrument &amp; strategy, then hit{" "}
        <span className="text-amber font-semibold">▸ RUN BACKTEST</span>
      </p>
    </div>
  );
}
