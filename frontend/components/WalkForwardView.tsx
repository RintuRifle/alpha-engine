"use client";

import { useState } from "react";
import type { WalkForwardResult } from "@/lib/api";
import { api, trackJob } from "@/lib/api";
import { fmtPct } from "@/lib/format";
import { Panel } from "./Panel";
import type { ConfigState } from "./ConfigPanel";

export function WalkForwardView({ config }: { config: ConfigState }) {
  const [nSplits, setNSplits] = useState(5);
  const [optimize, setOptimize] = useState(true);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState({ pct: 0, msg: "" });
  const [result, setResult] = useState<WalkForwardResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setRunning(true);
    setError(null);
    try {
      const { job_id } = await api.runWalkForward({
        ticker: config.ticker,
        start_date: config.start_date,
        end_date: config.end_date,
        interval: config.interval,
        strategy: config.strategy,
        params: config.params,
        n_splits: nSplits,
        capital: config.capital,
        optimize,
        embargo: 5,
      });
      setResult(
        await trackJob<WalkForwardResult>(job_id, (pct, msg) =>
          setProgress({ pct, msg })
        )
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  };

  if (config.strategy === "buy_and_hold")
    return (
      <Panel title="Walk-Forward Analysis">
        <p className="text-xxs text-dim">Not applicable to Buy &amp; Hold.</p>
      </Panel>
    );

  const maxAbs = result
    ? Math.max(
        0.01,
        ...result.windows.map((w) => Math.abs(w.test_return ?? 0))
      )
    : 1;

  return (
    <div className="space-y-3">
      <Panel title="Walk-Forward — Out-of-Sample Validation">
        <p className="text-micro text-dim font-sans mb-3 max-w-xl">
          Splits history into rolling train/test windows and only trades the
          unseen test segments. Consistent positive returns across windows =
          robust strategy; wild variation = overfit.
        </p>
        <div className="flex items-center gap-3 flex-wrap">
          <label className="flex items-center gap-2">
            <span className="microlabel">Windows</span>
            <input
              type="number"
              min={2}
              max={10}
              value={nSplits}
              onChange={(e) => setNSplits(Number(e.target.value))}
              className="!w-16"
            />
          </label>
          <button
            type="button"
            onClick={() => setOptimize((v) => !v)}
            className={`btn-ghost ${optimize ? "!text-amber !border-amber/60" : ""}`}
          >
            {optimize ? "◈ Optimized (train→freeze→test)" : "Fixed params"}
          </button>
          <button className="btn-primary" disabled={running} onClick={run}>
            {running ? `${progress.pct}% ${progress.msg}` : "Run Analysis"}
          </button>
          <span className="text-micro text-dim">embargo: 5 bars</span>
        </div>
        {error && <p className="text-xxs text-down mt-2">{error}</p>}
      </Panel>

      {result && (
        <>
          <Panel title="Window Returns (test segments only)" delay={0.05}>
            <div className="flex items-end gap-3 h-44 px-2">
              {result.windows.map((w) => {
                const r = w.test_return ?? 0;
                const h = (Math.abs(r) / maxAbs) * 80;
                return (
                  <div
                    key={w.window}
                    className="flex-1 flex flex-col items-center justify-end h-full"
                  >
                    <span
                      className={`text-xxs tabular-nums mb-1 ${
                        r >= 0 ? "text-up" : "text-down"
                      }`}
                    >
                      {fmtPct(r, 1)}
                    </span>
                    <div
                      className={`w-full max-w-[70px] rounded-sm transition-all duration-500 ${
                        r >= 0 ? "bg-up/70" : "bg-down/70"
                      }`}
                      style={{ height: `${Math.max(3, h)}%` }}
                    />
                    <span className="microlabel mt-2">W{w.window}</span>
                    <span className="text-micro text-dim">
                      {w.num_trades} trades
                    </span>
                    {w.params && (
                      <span
                        className="text-micro text-dim text-center leading-tight"
                        title="Params frozen from train-only optimization"
                      >
                        {Object.entries(w.params)
                          .map(([k, v]) => `${k.slice(0, 5)}=${v}`)
                          .join(" ")}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </Panel>

          <Panel title="Verdict" delay={0.1}>
            {result.degradation && (
              <div className="mb-3 flex items-center gap-4 flex-wrap font-mono text-xxs">
                <span className="microlabel">In-Sample vs Out-of-Sample Sharpe</span>
                <span className="tabular-nums text-muted">
                  train {result.degradation.avg_train_sharpe ?? "—"}
                </span>
                <span className="text-dim">→</span>
                <span
                  className={`tabular-nums font-semibold ${
                    (result.degradation.avg_test_sharpe ?? 0) >=
                    0.5 * (result.degradation.avg_train_sharpe ?? 0)
                      ? "text-up"
                      : "text-down"
                  }`}
                >
                  test {result.degradation.avg_test_sharpe ?? "—"}
                </span>
                <span className="text-micro text-dim font-sans">
                  large train→test drop = overfitting signal
                </span>
              </div>
            )}
            <div className="grid grid-cols-3 gap-px bg-line border border-line rounded-sm overflow-hidden">
              <div className="bg-panel px-3 py-2.5">
                <div className="microlabel">Avg Test Return</div>
                <div
                  className={`text-sm font-semibold tabular-nums ${
                    (result.summary.avg_return ?? 0) >= 0
                      ? "text-up"
                      : "text-down"
                  }`}
                >
                  {fmtPct(result.summary.avg_return)}
                </div>
              </div>
              <div className="bg-panel px-3 py-2.5">
                <div className="microlabel">Consistency</div>
                <div className="text-sm font-semibold tabular-nums">
                  {fmtPct(result.summary.consistency, 0)}
                </div>
              </div>
              <div className="bg-panel px-3 py-2.5">
                <div className="microlabel">Windows</div>
                <div className="text-sm font-semibold tabular-nums">
                  {result.summary.n_windows}
                </div>
              </div>
            </div>
            <p className="text-micro font-sans mt-2 text-muted">
              {(result.summary.consistency ?? 0) >= 0.6
                ? "✓ Majority of out-of-sample windows profitable — parameters generalize reasonably."
                : "⚠ Weak out-of-sample consistency — treat the in-sample results with suspicion."}
            </p>
          </Panel>
        </>
      )}
    </div>
  );
}
