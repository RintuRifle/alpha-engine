"use client";

import type { BacktestResult } from "@/lib/api";
import { fmtNum, fmtBarTime } from "@/lib/format";
import { Panel } from "./Panel";

const ACTION_COLOR: Record<string, string> = {
  BUY: "text-up",
  COVER: "text-up",
  SELL: "text-down",
  SHORT: "text-down",
};

export function TradesTable({ result }: { result: BacktestResult }) {
  if (!result.trades.length)
    return (
      <Panel title="Trade Blotter">
        <p className="text-xxs text-dim">No trades executed.</p>
      </Panel>
    );

  const downloadCsv = () => {
    const header = "date,action,quantity,price,commission,slippage";
    const rows = result.trades.map(
      (t) =>
        `${t.time},${t.action},${t.quantity},${t.price},${t.commission},${t.slippage}`
    );
    const blob = new Blob([[header, ...rows].join("\n")], {
      type: "text/csv",
    });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${result.ticker}_${result.strategy_key}_trades.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  return (
    <Panel
      title={`Trade Blotter — ${result.trades.length} executions`}
      right={
        <button className="btn-ghost !py-1" onClick={downloadCsv}>
          ↓ CSV
        </button>
      }
    >
      <div className="max-h-[540px] overflow-y-auto">
        <table className="term">
          <thead>
            <tr>
              <th>#</th>
              <th>Date</th>
              <th>Action</th>
              <th>Qty</th>
              <th>Price</th>
              <th>Notional</th>
              <th>Commission</th>
              <th>Slippage</th>
            </tr>
          </thead>
          <tbody>
            {result.trades.map((t, i) => (
              <tr key={i}>
                <td className="text-dim">{i + 1}</td>
                <td className="tabular-nums">{fmtBarTime(t.time)}</td>
                <td
                  className={`font-semibold ${ACTION_COLOR[t.action] ?? ""}`}
                >
                  {t.action}
                </td>
                <td className="tabular-nums">{t.quantity}</td>
                <td className="tabular-nums">${fmtNum(t.price)}</td>
                <td className="tabular-nums">
                  ${fmtNum((t.quantity ?? 0) * (t.price ?? 0))}
                </td>
                <td className="tabular-nums text-muted">
                  ${fmtNum(t.commission)}
                </td>
                <td className="tabular-nums text-muted">
                  ${fmtNum(t.slippage)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
