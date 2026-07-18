"use client";

import type { Time } from "lightweight-charts";
import { LineStyle } from "lightweight-charts";
import type { BacktestResult } from "@/lib/api";
import { CHART_COLORS } from "@/lib/chartTheme";
import { useChart } from "./useChart";

function intradayAxis(chart: Parameters<Parameters<typeof useChart>[1]>[0], result: BacktestResult) {
  if (result.interval && result.interval !== "1d") {
    chart.applyOptions({
      timeScale: { timeVisible: true, secondsVisible: false },
    });
  }
}

export function EquityChart({ result }: { result: BacktestResult }) {
  const ref = useChart(
    340,
    (chart) => {
      intradayAxis(chart, result);
      const eq = chart.addAreaSeries({
        lineColor: CHART_COLORS.amber,
        topColor: "rgba(247,166,0,0.22)",
        bottomColor: "rgba(247,166,0,0.0)",
        lineWidth: 2,
        priceFormat: { type: "price", precision: 0, minMove: 1 },
      });
      eq.setData(
        result.equity.map((p) => ({ time: p.time as Time, value: p.equity }))
      );

      if (result.benchmark) {
        const bench = chart.addLineSeries({
          color: CHART_COLORS.cyan,
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          priceFormat: { type: "price", precision: 0, minMove: 1 },
        });
        bench.setData(
          result.benchmark.map((p) => ({
            time: p.time as Time,
            value: p.equity,
          }))
        );
      }
    },
    [result]
  );

  return (
    <div>
      <div ref={ref} className="w-full" />
      <div className="flex gap-4 mt-1 px-1">
        <span className="flex items-center gap-1.5 text-micro text-muted">
          <span className="w-3 h-0.5 bg-amber inline-block" /> STRATEGY
        </span>
        {result.benchmark && (
          <span className="flex items-center gap-1.5 text-micro text-muted">
            <span className="w-3 h-0.5 bg-cyan inline-block" /> BENCHMARK
          </span>
        )}
      </div>
    </div>
  );
}

export function DrawdownChart({ result }: { result: BacktestResult }) {
  const ref = useChart(
    220,
    (chart) => {
      intradayAxis(chart, result);
      const dd = chart.addAreaSeries({
        lineColor: CHART_COLORS.down,
        topColor: "rgba(246,70,93,0.0)",
        bottomColor: "rgba(246,70,93,0.28)",
        lineWidth: 1,
        priceFormat: {
          type: "custom",
          formatter: (v: number) => `${(v * 100).toFixed(1)}%`,
        },
      });
      dd.setData(
        result.equity.map((p) => ({ time: p.time as Time, value: p.drawdown }))
      );
    },
    [result]
  );
  return <div ref={ref} className="w-full" />;
}

export function RollingChart({ result }: { result: BacktestResult }) {
  const ref = useChart(
    240,
    (chart) => {
      intradayAxis(chart, result);
      const sharpe = chart.addLineSeries({
        color: CHART_COLORS.amber,
        lineWidth: 2,
        priceFormat: { type: "price", precision: 2, minMove: 0.01 },
      });
      sharpe.setData(
        result.rolling
          .filter((r) => r.sharpe != null)
          .map((r) => ({ time: r.time as Time, value: r.sharpe as number }))
      );
      const sortino = chart.addLineSeries({
        color: CHART_COLORS.violet,
        lineWidth: 1,
      });
      sortino.setData(
        result.rolling
          .filter((r) => r.sortino != null)
          .map((r) => ({ time: r.time as Time, value: r.sortino as number }))
      );
    },
    [result]
  );
  return (
    <div>
      <div ref={ref} className="w-full" />
      <div className="flex gap-4 mt-1 px-1">
        <span className="flex items-center gap-1.5 text-micro text-muted">
          <span className="w-3 h-0.5 bg-amber inline-block" /> SHARPE (60D)
        </span>
        <span className="flex items-center gap-1.5 text-micro text-muted">
          <span className="w-3 h-0.5 bg-violet inline-block" /> SORTINO (60D)
        </span>
      </div>
    </div>
  );
}
