"use client";

import type { CompareResult } from "@/lib/api";
import { fmtPct, fmtNum, fmtMoney } from "@/lib/format";
import { Panel } from "./Panel";

export function CompareView({ result }: { result: CompareResult | null }) {
  if (!result)
    return (
      <Panel title="Strategy Arena">
        <p className="text-xxs text-dim">
          Press <span className="text-amber">COMPARE ALL STRATEGIES</span> in
          the left panel to battle all strategies on {`the current instrument`}.
        </p>
      </Panel>
    );

  const ok = result.results.filter((r) => !r.error);
  const errs = result.results.filter((r) => r.error);

  return (
    <div className="space-y-3">
      <Panel
        title={`Strategy Arena — ${result.ticker} (ranked by composite robustness)`}
      >
        <div className="overflow-x-auto">
          <table className="term">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Strategy</th>
                <th title="Composite: Sharpe + Calmar + drawdown + profit factor, discounted for low trade counts">
                  Robust
                </th>
                <th>Total Ret</th>
                <th>CAGR</th>
                <th>Sharpe</th>
                <th>Sortino</th>
                <th>Max DD</th>
                <th>Win Rate</th>
                <th>PF</th>
                <th>Trades</th>
                <th>Final Equity</th>
              </tr>
            </thead>
            <tbody>
              {ok.map((r, i) => {
                const m = r.metrics!;
                return (
                  <tr key={r.key} className={i === 0 ? "bg-amber/5" : ""}>
                    <td>
                      {i === 0 ? (
                        <span className="text-amber font-bold">★ 1</span>
                      ) : (
                        <span className="text-dim">{i + 1}</span>
                      )}
                    </td>
                    <td className={i === 0 ? "text-amber font-semibold" : ""}>
                      {r.label}
                    </td>
                    <td className="tabular-nums font-semibold">
                      {r.robustness ?? "—"}
                    </td>
                    <td
                      className={`tabular-nums ${
                        (m.total_return ?? 0) >= 0 ? "text-up" : "text-down"
                      }`}
                    >
                      {fmtPct(m.total_return)}
                    </td>
                    <td className="tabular-nums">{fmtPct(m.cagr)}</td>
                    <td className="tabular-nums font-semibold">
                      {fmtNum(m.sharpe_ratio)}
                    </td>
                    <td className="tabular-nums">{fmtNum(m.sortino_ratio)}</td>
                    <td className="tabular-nums text-down">
                      {fmtPct(m.max_drawdown)}
                    </td>
                    <td className="tabular-nums">{fmtPct(m.win_rate, 0)}</td>
                    <td className="tabular-nums">{fmtNum(m.profit_factor)}</td>
                    <td className="tabular-nums">{m.total_trades ?? "—"}</td>
                    <td className="tabular-nums">{fmtMoney(r.final_equity)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {errs.length > 0 && (
          <div className="mt-2 space-y-1">
            {errs.map((r) => (
              <p key={r.key} className="text-xxs text-down">
                {r.label}: {r.error}
              </p>
            ))}
          </div>
        )}
      </Panel>

      <Panel title="Normalized Equity Curves" delay={0.05}>
        <SparkGrid result={result} />
      </Panel>
    </div>
  );
}

/** Mini SVG sparklines per strategy — cheap, no chart lib needed. */
function SparkGrid({ result }: { result: CompareResult }) {
  const ok = result.results.filter((r) => !r.error && r.equity?.length);
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
      {ok.map((r, idx) => {
        const eq = r.equity!;
        const vals = eq.map((p) => p.equity);
        const lo = Math.min(...vals);
        const hi = Math.max(...vals);
        const W = 220;
        const H = 60;
        const pts = vals
          .map(
            (v, i) =>
              `${((i / (vals.length - 1)) * W).toFixed(1)},${(
                H -
                ((v - lo) / Math.max(1e-9, hi - lo)) * H
              ).toFixed(1)}`
          )
          .join(" ");
        const ret = vals[vals.length - 1] / vals[0] - 1;
        return (
          <div
            key={r.key}
            className="border border-line rounded-sm p-2 bg-panel2 hover:border-dim transition-colors"
          >
            <div className="flex justify-between items-baseline mb-1">
              <span className="text-xxs text-muted">{r.label}</span>
              <span
                className={`text-xxs tabular-nums font-semibold ${
                  ret >= 0 ? "text-up" : "text-down"
                }`}
              >
                {fmtPct(ret, 1)}
              </span>
            </div>
            <svg
              viewBox={`0 0 ${W} ${H}`}
              className="w-full h-14"
              preserveAspectRatio="none"
            >
              <polyline
                points={pts}
                fill="none"
                stroke={idx === 0 ? "#f7a600" : ret >= 0 ? "#0ecb81" : "#f6465d"}
                strokeWidth="1.5"
                vectorEffect="non-scaling-stroke"
              />
            </svg>
          </div>
        );
      })}
    </div>
  );
}
