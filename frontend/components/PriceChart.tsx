"use client";

import type { Time, SeriesMarker } from "lightweight-charts";
import type { BacktestResult } from "@/lib/api";
import { CHART_COLORS } from "@/lib/chartTheme";
import { useChart } from "./useChart";

export function PriceChart({ result }: { result: BacktestResult }) {
  const ref = useChart(
    460,
    (chart) => {
      const candles = chart.addCandlestickSeries({
        upColor: CHART_COLORS.up,
        downColor: CHART_COLORS.down,
        borderUpColor: CHART_COLORS.up,
        borderDownColor: CHART_COLORS.down,
        wickUpColor: CHART_COLORS.up,
        wickDownColor: CHART_COLORS.down,
      });
      candles.setData(
        result.candles.map((c) => ({
          time: c.time as Time,
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
        }))
      );

      const vol = chart.addHistogramSeries({
        priceScaleId: "vol",
        priceFormat: { type: "volume" },
        color: "#22304a",
      });
      chart.priceScale("vol").applyOptions({
        scaleMargins: { top: 0.85, bottom: 0 },
      });
      vol.setData(
        result.candles.map((c) => ({
          time: c.time as Time,
          value: c.volume ?? 0,
          color:
            c.close >= c.open
              ? "rgba(14,203,129,0.25)"
              : "rgba(246,70,93,0.25)",
        }))
      );

      const markers: SeriesMarker<Time>[] = result.trades.map((t) => {
        const isEntry = t.action === "BUY" || t.action === "COVER";
        return {
          time: t.time as Time,
          position: isEntry ? "belowBar" : "aboveBar",
          color: isEntry ? CHART_COLORS.up : CHART_COLORS.down,
          shape: isEntry ? "arrowUp" : "arrowDown",
          text: `${t.action} ${t.quantity ?? ""}`,
          size: 1,
        };
      });
      candles.setMarkers(markers);
    },
    [result]
  );

  return <div ref={ref} className="w-full" />;
}
