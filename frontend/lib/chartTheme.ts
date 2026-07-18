import { ColorType, CrosshairMode, type DeepPartial, type ChartOptions } from "lightweight-charts";

export const CHART_COLORS = {
  up: "#0ecb81",
  down: "#f6465d",
  amber: "#f7a600",
  cyan: "#22d3ee",
  violet: "#a78bfa",
  muted: "#5b6b7d",
  grid: "#131c27",
};

export function baseChartOptions(height: number): DeepPartial<ChartOptions> {
  return {
    height,
    layout: {
      background: { type: ColorType.Solid, color: "transparent" },
      textColor: "#5b6b7d",
      fontFamily: "var(--font-mono), ui-monospace, monospace",
      fontSize: 10,
    },
    grid: {
      vertLines: { color: CHART_COLORS.grid },
      horzLines: { color: CHART_COLORS.grid },
    },
    crosshair: {
      mode: CrosshairMode.Normal,
      vertLine: { color: "#3b4a5c", labelBackgroundColor: "#182230" },
      horzLine: { color: "#3b4a5c", labelBackgroundColor: "#182230" },
    },
    rightPriceScale: { borderColor: "#182230" },
    timeScale: { borderColor: "#182230", timeVisible: false },
    autoSize: false,
  };
}
