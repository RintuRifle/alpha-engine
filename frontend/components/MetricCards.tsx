"use client";

import { motion } from "framer-motion";
import { AnimatedNumber } from "./AnimatedNumber";
import { fmtMoney } from "@/lib/format";

interface CardDef {
  label: string;
  value: number | null | undefined;
  format: (v: number) => string;
  colorize?: boolean;
  invert?: boolean;
}

export function MetricCards({
  metrics,
}: {
  metrics: Record<string, number | null>;
}) {
  const cards: CardDef[] = [
    {
      label: "Total Return",
      value: metrics.total_return,
      format: (v) => `${(v * 100).toFixed(2)}%`,
      colorize: true,
    },
    {
      label: "CAGR",
      value: metrics.cagr,
      format: (v) => `${(v * 100).toFixed(2)}%`,
      colorize: true,
    },
    {
      label: "Sharpe",
      value: metrics.sharpe_ratio,
      format: (v) => v.toFixed(2),
      colorize: true,
    },
    {
      label: "Sortino",
      value: metrics.sortino_ratio,
      format: (v) => v.toFixed(2),
      colorize: true,
    },
    {
      label: "Max Drawdown",
      value: metrics.max_drawdown,
      format: (v) => `${(v * 100).toFixed(2)}%`,
      colorize: true,
    },
    {
      label: "Volatility",
      value: metrics.volatility,
      format: (v) => `${(v * 100).toFixed(1)}%`,
    },
    {
      label: "Win Rate",
      value: metrics.win_rate,
      format: (v) => `${(v * 100).toFixed(1)}%`,
    },
    {
      label: "Profit Factor",
      value: metrics.profit_factor,
      format: (v) => v.toFixed(2),
    },
    {
      label: "Calmar",
      value: metrics.calmar_ratio,
      format: (v) => v.toFixed(2),
    },
    {
      label: "Trades",
      value: metrics.total_trades,
      format: (v) => v.toFixed(0),
    },
    {
      label: "Final Equity",
      value: metrics.final_equity,
      format: (v) => fmtMoney(v),
    },
    {
      label: "Benchmark Ret",
      value: metrics.benchmark_return,
      format: (v) => `${(v * 100).toFixed(2)}%`,
      colorize: true,
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-px bg-line border border-line rounded-sm overflow-hidden">
      {cards.map((c, i) => {
        const color = c.colorize
          ? c.value == null
            ? "text-muted"
            : (c.value >= 0) !== !!c.invert
            ? "text-up"
            : "text-down"
          : "text-text";
        return (
          <motion.div
            key={c.label}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.03, duration: 0.3 }}
            className="bg-panel px-3 py-2.5"
          >
            <div className="microlabel">{c.label}</div>
            <AnimatedNumber
              value={c.value}
              format={c.format}
              className={`text-sm font-semibold tabular-nums ${color}`}
            />
          </motion.div>
        );
      })}
    </div>
  );
}
