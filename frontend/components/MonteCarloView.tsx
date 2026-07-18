"use client";

import type { Time } from "lightweight-charts";
import { LineStyle } from "lightweight-charts";
import type { BacktestResult } from "@/lib/api";
import { CHART_COLORS } from "@/lib/chartTheme";
import { useChart } from "./useChart";
import { fmtPct, fmtNum } from "@/lib/format";
import { Panel } from "./Panel";

/** Fake future dates for the x-axis (252 bars projected forward). */
function mcTime(i: number, last: string | number): string {
  const d =
    typeof last === "number" ? new Date(last * 1000) : new Date(last);
  d.setDate(d.getDate() + Math.round((i + 1) * 1.45));
  return d.toISOString().slice(0, 10);
}

export function MonteCarloView({ result }: { result: BacktestResult }) {
  const mc = result.monte_carlo;
  const last: string | number =
    result.equity[result.equity.length - 1]?.time ?? "2026-01-01";

  const ref = useChart(
    320,
    (chart) => {
      if (!mc) return;
      const bands: [number[], number[], string][] = [
        [mc.p05, mc.p95, "rgba(247,166,0,0.10)"],
        [mc.p25, mc.p75, "rgba(247,166,0,0.18)"],
      ];
      // draw envelope bands as area pairs
      for (const [lo, hi, color] of bands) {
        const hiSeries = chart.addAreaSeries({
          lineColor: "transparent",
          topColor: color,
          bottomColor: color,
          lineWidth: 1,
          priceFormat: { type: "price", precision: 2, minMove: 0.01 },
        });
        hiSeries.setData(
          hi.map((v, i) => ({ time: mcTime(i, last) as Time, value: v }))
        );
        const loSeries = chart.addAreaSeries({
          lineColor: "transparent",
          topColor: "#07090c",
          bottomColor: "#07090c",
          lineWidth: 1,
        });
        loSeries.setData(
          lo.map((v, i) => ({ time: mcTime(i, last) as Time, value: v }))
        );
      }
      for (const [key, color, width, style] of [
        ["p05", CHART_COLORS.down, 1, LineStyle.Dashed],
        ["p50", CHART_COLORS.amber, 2, LineStyle.Solid],
        ["p95", CHART_COLORS.up, 1, LineStyle.Dashed],
      ] as const) {
        const s = chart.addLineSeries({
          color: color as string,
          lineWidth: width as 1 | 2,
          lineStyle: style,
          priceFormat: { type: "price", precision: 2, minMove: 0.01 },
        });
        s.setData(
          (mc[key] as number[]).map((v, i) => ({
            time: mcTime(i, last) as Time,
            value: v,
          }))
        );
      }
    },
    [mc]
  );

  if (!mc)
    return (
      <Panel title="Monte Carlo">
        <p className="text-xxs text-dim">No simulation data.</p>
      </Panel>
    );

  const stats = mc.stats || {};

  return (
    <div className="space-y-3">
      <Panel title="Monte Carlo — 1Y Forward Projection (normalized, 500 paths)">
        <div ref={ref} className="w-full" />
        <div className="flex gap-4 mt-1 px-1 flex-wrap">
          <span className="flex items-center gap-1.5 text-micro text-muted">
            <span className="w-3 h-0.5 bg-amber inline-block" /> MEDIAN
          </span>
          <span className="flex items-center gap-1.5 text-micro text-muted">
            <span className="w-3 h-0.5 bg-up inline-block" /> P95
          </span>
          <span className="flex items-center gap-1.5 text-micro text-muted">
            <span className="w-3 h-0.5 bg-down inline-block" /> P05
          </span>
        </div>
      </Panel>

      <Panel title="Projection Statistics" delay={0.05}>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-line border border-line rounded-sm overflow-hidden">
          {[
            ["Median Final", stats.median_final, "x"],
            ["Prob. of Profit", stats.prob_profit, "%"],
            ["Worst Case (5%)", stats.worst_case_5pct, "x"],
            ["Prob. 20%+ Loss", stats.prob_loss_20pct, "%"],
          ].map(([label, v, unit]) => (
            <div key={label as string} className="bg-panel px-3 py-2.5">
              <div className="microlabel">{label as string}</div>
              <div className="text-sm font-semibold tabular-nums">
                {v == null
                  ? "—"
                  : unit === "%"
                  ? fmtPct(v as number, 1)
                  : `${fmtNum(v as number, 2)}x`}
              </div>
            </div>
          ))}
        </div>
      </Panel>

      {mc.stress && mc.stress.length > 0 && (
        <Panel title="Historical Stress Scenarios" delay={0.1}>
          <div className="overflow-x-auto max-h-64 overflow-y-auto">
            <table className="term">
              <thead>
                <tr>
                  {Object.keys(mc.stress[0]).map((k) => (
                    <th key={k}>{k.replace(/_/g, " ")}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {mc.stress.map((row, i) => (
                  <tr key={i}>
                    {Object.entries(row).map(([k, v]) => (
                      <td key={k} className="tabular-nums">
                        {typeof v === "number"
                          ? Math.abs(v) < 1
                            ? fmtPct(v)
                            : fmtNum(v)
                          : String(v)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}
    </div>
  );
}
