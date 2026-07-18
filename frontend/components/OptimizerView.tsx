"use client";

import { useMemo, useState } from "react";
import type { StrategySchema, OptimizeResult } from "@/lib/api";
import { api, trackJob } from "@/lib/api";
import { buildRange, fmtNum, fmtPct } from "@/lib/format";
import { Panel } from "./Panel";
import type { ConfigState } from "./ConfigPanel";

const METRICS = [
  ["sharpe_ratio", "Sharpe Ratio"],
  ["sortino_ratio", "Sortino Ratio"],
  ["calmar_ratio", "Calmar Ratio"],
  ["cagr", "CAGR"],
  ["total_return", "Total Return"],
];

interface GridRow {
  param: string;
  label: string;
  min: number;
  max: number;
  step: number;
  enabled: boolean;
}

function heatColor(v: number | null, lo: number, hi: number) {
  if (v == null) return { background: "transparent" };
  const t = hi === lo ? 0.5 : (v - lo) / (hi - lo);
  return {
    background: `rgba(247, 166, 0, ${0.06 + t * 0.75})`,
    color: t > 0.65 ? "#07090c" : "#d7e0ea",
  };
}

export function OptimizerView({
  config,
  strategies,
}: {
  config: ConfigState;
  strategies: StrategySchema[];
}) {
  const strat = strategies.find((s) => s.key === config.strategy);
  const [metric, setMetric] = useState("sharpe_ratio");
  const [rows, setRows] = useState<GridRow[]>([]);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState({ pct: 0, msg: "" });
  const [result, setResult] = useState<OptimizeResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // (re)build grid rows when strategy changes
  useMemo(() => {
    if (!strat) return;
    setRows(
      strat.params.map((p, i) => ({
        param: p.name,
        label: p.label,
        min: p.min,
        max: p.max,
        step: p.step * 2,
        enabled: i < 2,
      }))
    );
    setResult(null);
  }, [strat?.key]); // eslint-disable-line react-hooks/exhaustive-deps

  const enabled = rows.filter((r) => r.enabled);
  const combos = enabled.reduce(
    (acc, r) => acc * buildRange(r.min, r.max, r.step).length,
    1
  );

  const run = async () => {
    if (!strat || enabled.length === 0) return;
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const grid: Record<string, number[]> = {};
      enabled.forEach((r) => (grid[r.param] = buildRange(r.min, r.max, r.step)));
      const { job_id } = await api.runOptimize({
        ticker: config.ticker,
        start_date: config.start_date,
        end_date: config.end_date,
        interval: config.interval,
        strategy: config.strategy,
        param_grid: grid,
        metric,
        capital: config.capital,
      });
      const res = await trackJob<OptimizeResult>(job_id, (pct, msg) =>
        setProgress({ pct, msg })
      );
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  };

  if (!strat || config.strategy === "buy_and_hold" || config.strategy === "custom")
    return (
      <Panel title="Parameter Optimizer">
        <p className="text-xxs text-dim">
          Select a parameterized strategy (not Buy &amp; Hold / Custom) to
          optimize.
        </p>
      </Panel>
    );

  const flatZ =
    result?.heatmap?.z_values.flat().filter((v): v is number => v != null) ??
    [];
  const zLo = flatZ.length ? Math.min(...flatZ) : 0;
  const zHi = flatZ.length ? Math.max(...flatZ) : 1;

  return (
    <div className="space-y-3">
      <Panel title={`Grid Search — ${strat.label}`}>
        <div className="space-y-2.5">
          {rows.map((r, i) => (
            <div key={r.param} className="flex items-center gap-2 flex-wrap">
              <button
                onClick={() =>
                  setRows((rs) =>
                    rs.map((x, j) =>
                      j === i ? { ...x, enabled: !x.enabled } : x
                    )
                  )
                }
                className={`w-3.5 h-3.5 border rounded-[2px] shrink-0 transition-colors ${
                  r.enabled ? "bg-amber border-amber" : "border-dim"
                }`}
              />
              <span className="text-xxs text-muted w-32">{r.label}</span>
              {(["min", "max", "step"] as const).map((f) => (
                <label key={f} className="flex items-center gap-1">
                  <span className="microlabel">{f}</span>
                  <input
                    type="number"
                    value={r[f]}
                    step="any"
                    disabled={!r.enabled}
                    onChange={(e) =>
                      setRows((rs) =>
                        rs.map((x, j) =>
                          j === i
                            ? { ...x, [f]: Number(e.target.value) }
                            : x
                        )
                      )
                    }
                    className="!w-20 disabled:opacity-30"
                  />
                </label>
              ))}
            </div>
          ))}
        </div>

        <div className="flex items-center gap-3 mt-4 flex-wrap">
          <select
            value={metric}
            onChange={(e) => setMetric(e.target.value)}
            className="!w-44"
          >
            {METRICS.map(([k, l]) => (
              <option key={k} value={k}>
                {l}
              </option>
            ))}
          </select>
          <button
            className="btn-primary"
            disabled={running || combos === 0 || combos > 2000}
            onClick={run}
          >
            {running ? `${progress.pct}% ${progress.msg}` : `Optimize (${combos} combos)`}
          </button>
          {combos > 2000 && (
            <span className="text-xxs text-down">
              Grid too large — max 2000 combinations
            </span>
          )}
        </div>
        {error && <p className="text-xxs text-down mt-2">{error}</p>}
      </Panel>

      {result && (
        <>
          <Panel title="Best Parameters" delay={0.05}>
            <div className="flex items-center gap-6 flex-wrap">
              {Object.entries(result.best_params).map(([k, v]) => (
                <div key={k}>
                  <div className="microlabel">{k}</div>
                  <div className="text-lg font-bold text-amber tabular-nums">
                    {v}
                  </div>
                </div>
              ))}
              <div>
                <div className="microlabel">{result.metric}</div>
                <div className="text-lg font-bold text-up tabular-nums">
                  {fmtNum(result.best_value)}
                </div>
              </div>
              <div>
                <div className="microlabel">Tested</div>
                <div className="text-lg font-bold tabular-nums">
                  {result.total_combinations}
                  <span className="text-xxs text-muted ml-1">
                    in {result.elapsed_seconds}s
                  </span>
                </div>
              </div>
            </div>
          </Panel>

          {result.heatmap && (
            <Panel
              title={`Sensitivity Surface — ${result.heatmap.y_param} × ${result.heatmap.x_param}`}
              delay={0.1}
            >
              <div className="overflow-x-auto">
                <table className="font-mono text-xxs border-collapse">
                  <thead>
                    <tr>
                      <th className="microlabel pr-2 pb-1 text-right">
                        {result.heatmap.y_param}↓
                      </th>
                      {result.heatmap.x_values.map((x) => (
                        <th key={x} className="microlabel px-1 pb-1 text-center">
                          {x}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.heatmap.y_values.map((y, yi) => (
                      <tr key={y}>
                        <td className="pr-2 text-right text-muted tabular-nums">
                          {y}
                        </td>
                        {result.heatmap!.z_values[yi].map((z, xi) => {
                          const isBest =
                            result.best_params[result.heatmap!.y_param] === y &&
                            result.best_params[result.heatmap!.x_param] ===
                              result.heatmap!.x_values[xi];
                          return (
                            <td key={xi} className="p-0.5">
                              <div
                                className={`px-2 py-1.5 rounded-[2px] text-center tabular-nums min-w-[52px] transition-transform hover:scale-110 ${
                                  isBest ? "ring-1 ring-up" : ""
                                }`}
                                style={heatColor(z, zLo, zHi)}
                                title={`${result.heatmap!.y_param}=${y}, ${
                                  result.heatmap!.x_param
                                }=${result.heatmap!.x_values[xi]} → ${fmtNum(z)}`}
                              >
                                {z == null ? "·" : z.toFixed(2)}
                              </div>
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-micro text-dim mt-2 font-sans">
                Flat bright plateaus = robust parameter zones. Isolated bright
                cells = likely overfitting.
              </p>
            </Panel>
          )}

          <Panel title="Top Results" delay={0.15}>
            <div className="max-h-72 overflow-y-auto">
              <table className="term">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Params</th>
                    <th>{result.metric}</th>
                    <th>CAGR</th>
                    <th>Max DD</th>
                  </tr>
                </thead>
                <tbody>
                  {result.top_results.map((r, i) => (
                    <tr key={i}>
                      <td className="text-dim">{i + 1}</td>
                      <td className="text-amber">
                        {Object.entries(r.params)
                          .map(([k, v]) => `${k}=${v}`)
                          .join("  ")}
                      </td>
                      <td className="tabular-nums">{fmtNum(r.value)}</td>
                      <td className="tabular-nums">{fmtPct(r.cagr)}</td>
                      <td className="tabular-nums text-down">
                        {fmtPct(r.max_drawdown)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </>
      )}
    </div>
  );
}
