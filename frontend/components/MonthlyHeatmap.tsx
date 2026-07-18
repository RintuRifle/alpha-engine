"use client";

import type { BacktestResult } from "@/lib/api";
import { MONTHS, fmtPct } from "@/lib/format";

function cellStyle(v: number | null) {
  if (v == null) return { background: "transparent" };
  const capped = Math.max(-0.15, Math.min(0.15, v));
  const alpha = Math.min(0.85, Math.abs(capped) / 0.15);
  return v >= 0
    ? { background: `rgba(14, 203, 129, ${alpha * 0.55})` }
    : { background: `rgba(246, 70, 93, ${alpha * 0.55})` };
}

export function MonthlyHeatmap({
  monthly,
}: {
  monthly: BacktestResult["monthly_returns"];
}) {
  if (!monthly.years.length)
    return <p className="text-xxs text-dim">No monthly data.</p>;

  return (
    <div className="overflow-x-auto">
      <table className="font-mono text-xxs border-collapse min-w-full">
        <thead>
          <tr>
            <th className="microlabel text-left pr-3 py-1.5">Year</th>
            {MONTHS.map((m) => (
              <th key={m} className="microlabel px-1.5 py-1.5 text-center">
                {m}
              </th>
            ))}
            <th className="microlabel pl-3 py-1.5 text-right">YTD</th>
          </tr>
        </thead>
        <tbody>
          {monthly.years.map((y, yi) => (
            <tr key={y}>
              <td className="pr-3 py-0.5 text-muted">{y}</td>
              {monthly.data[yi].map((v, mi) => (
                <td key={mi} className="p-0.5">
                  <div
                    className="px-1.5 py-1 rounded-[2px] text-center tabular-nums min-w-[46px]"
                    style={cellStyle(v)}
                    title={v == null ? "" : fmtPct(v)}
                  >
                    {v == null ? (
                      <span className="text-dim">·</span>
                    ) : (
                      <span className={v >= 0 ? "text-up" : "text-down"}>
                        {(v * 100).toFixed(1)}
                      </span>
                    )}
                  </div>
                </td>
              ))}
              <td
                className={`pl-3 py-0.5 text-right font-semibold tabular-nums ${
                  (monthly.yearly[yi] ?? 0) >= 0 ? "text-up" : "text-down"
                }`}
              >
                {fmtPct(monthly.yearly[yi], 1)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
