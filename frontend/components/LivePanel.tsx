"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { fmtMoney, fmtPct, signColor } from "@/lib/format";
import { Panel } from "./Panel";

export function LivePanel() {
  const [account, setAccount] = useState<Record<string, unknown> | null>(null);
  const [positions, setPositions] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = () => {
    setLoading(true);
    setError(null);
    Promise.all([api.liveAccount(), api.livePositions()])
      .then(([acc, pos]) => {
        setAccount(acc);
        setPositions(pos.positions);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 30000);
    return () => clearInterval(t);
  }, []);

  if (error)
    return (
      <Panel title="Live Brokerage — Alpaca (paper)">
        <p className="text-xxs text-down mb-2">{error}</p>
        <p className="text-micro text-dim font-sans max-w-lg">
          Read-only PnL view. Set ALPACA_API_KEY and ALPACA_SECRET_KEY as
          environment variables on the backend (Render dashboard → Environment)
          to connect your paper trading account.
        </p>
        <button className="btn-ghost mt-3" onClick={refresh}>
          Retry
        </button>
      </Panel>
    );

  return (
    <div className="space-y-3">
      <Panel
        title="Account — Alpaca Paper"
        right={
          <button className="btn-ghost !py-1" onClick={refresh}>
            {loading ? "..." : "⟳ Refresh"}
          </button>
        }
      >
        {account ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-line border border-line rounded-sm overflow-hidden">
            {[
              ["Equity", account.equity],
              ["Portfolio Value", account.portfolio_value],
              ["Cash", account.cash],
              ["Buying Power", account.buying_power],
            ].map(([label, v]) => (
              <div key={label as string} className="bg-panel px-3 py-2.5">
                <div className="microlabel">{label as string}</div>
                <div className="text-sm font-semibold tabular-nums">
                  {fmtMoney(v as number)}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="skeleton h-16 rounded-sm" />
        )}
      </Panel>

      <Panel title={`Open Positions (${positions.length})`} delay={0.05}>
        {positions.length === 0 ? (
          <p className="text-xxs text-dim">No open positions.</p>
        ) : (
          <table className="term">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Qty</th>
                <th>Market Value</th>
                <th>Unrealized PnL</th>
                <th>PnL %</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((p, i) => (
                <tr key={i}>
                  <td className="text-amber font-semibold">
                    {String(p.symbol)}
                  </td>
                  <td className="tabular-nums">{String(p.qty)}</td>
                  <td className="tabular-nums">
                    {fmtMoney(p.market_value as number)}
                  </td>
                  <td
                    className={`tabular-nums font-semibold ${signColor(
                      p.unrealized_pl as number
                    )}`}
                  >
                    {fmtMoney(p.unrealized_pl as number)}
                  </td>
                  <td
                    className={`tabular-nums ${signColor(
                      p.unrealized_plpc as number
                    )}`}
                  >
                    {fmtPct(p.unrealized_plpc as number)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </div>
  );
}
