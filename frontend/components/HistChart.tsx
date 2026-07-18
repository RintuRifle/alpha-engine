"use client";

import type { BacktestResult } from "@/lib/api";
import { fmtNum } from "@/lib/format";

export function HistChart({
  hist,
}: {
  hist: BacktestResult["returns_hist"];
}) {
  if (!hist.bins.length)
    return <p className="text-xxs text-dim">No return data.</p>;
  const max = Math.max(...hist.counts);

  return (
    <div>
      <div className="flex items-end gap-px h-40">
        {hist.bins.map((b, i) => (
          <div
            key={i}
            className="flex-1 group relative"
            style={{ height: "100%" }}
          >
            <div
              className={`absolute bottom-0 w-full transition-all duration-300 ${
                b >= 0 ? "bg-up/60 group-hover:bg-up" : "bg-down/60 group-hover:bg-down"
              }`}
              style={{ height: `${(hist.counts[i] / max) * 100}%` }}
              title={`${(b * 100).toFixed(2)}% × ${hist.counts[i]}`}
            />
          </div>
        ))}
      </div>
      <div className="flex justify-between text-micro text-dim mt-1 tabular-nums">
        <span>{(hist.bins[0] * 100).toFixed(1)}%</span>
        <span>0%</span>
        <span>{(hist.bins[hist.bins.length - 1] * 100).toFixed(1)}%</span>
      </div>
      <div className="grid grid-cols-4 gap-px bg-line border border-line rounded-sm mt-3 overflow-hidden">
        {[
          ["Daily Mean", hist.mean == null ? null : hist.mean * 100, "%"],
          ["Daily Std", hist.std == null ? null : hist.std * 100, "%"],
          ["Skew", hist.skew, ""],
          ["Kurtosis", hist.kurtosis, ""],
        ].map(([label, v, suffix]) => (
          <div key={label as string} className="bg-panel px-3 py-2">
            <div className="microlabel">{label as string}</div>
            <div className="text-xs font-semibold tabular-nums">
              {v == null ? "—" : `${fmtNum(v as number, 3)}${suffix}`}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
