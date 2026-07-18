"use client";

import { useEffect, useRef } from "react";
import { createChart, type IChartApi } from "lightweight-charts";
import { baseChartOptions } from "@/lib/chartTheme";

/**
 * Manages a lightweight-charts instance lifecycle + responsive width.
 * `build` is called once per data change with a fresh chart.
 */
export function useChart(
  height: number,
  build: (chart: IChartApi) => void,
  deps: unknown[]
) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const chart = createChart(el, {
      ...baseChartOptions(height),
      width: el.clientWidth,
    });
    build(chart);
    chart.timeScale().fitContent();

    const ro = new ResizeObserver(() => {
      chart.applyOptions({ width: el.clientWidth });
    });
    ro.observe(el);

    return () => {
      ro.disconnect();
      chart.remove();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return containerRef;
}
