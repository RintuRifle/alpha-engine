"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export function TopBar({
  ticker,
  strategyLabel,
}: {
  ticker: string;
  strategyLabel: string;
}) {
  const [apiUp, setApiUp] = useState<boolean | null>(null);
  const [clock, setClock] = useState("");

  useEffect(() => {
    let alive = true;
    const check = () =>
      api
        .health()
        .then(() => alive && setApiUp(true))
        .catch(() => alive && setApiUp(false));
    check();
    const h = setInterval(check, 30000);
    const c = setInterval(() => {
      setClock(new Date().toUTCString().slice(17, 25) + " UTC");
    }, 1000);
    return () => {
      alive = false;
      clearInterval(h);
      clearInterval(c);
    };
  }, []);

  return (
    <header className="h-12 flex items-center justify-between px-4 border-b border-line bg-panel/80 backdrop-blur-sm sticky top-0 z-40">
      <div className="flex items-center gap-3">
        <div className="flex items-baseline gap-0.5 select-none">
          <span className="text-amber font-bold tracking-[0.22em] text-sm">
            ALPHA
          </span>
          <span className="text-text font-bold tracking-[0.22em] text-sm">
            ENGINE
          </span>
          <span className="text-amber animate-blink font-bold">_</span>
        </div>
        <span className="text-dim text-micro hidden md:inline">
          QUANT RESEARCH TERMINAL v2
        </span>
      </div>

      <div className="flex items-center gap-4 font-mono text-xxs">
        <div className="hidden sm:flex items-center gap-2 text-muted">
          <span className="text-amber font-semibold">{ticker}</span>
          <span className="text-dim">/</span>
          <span>{strategyLabel}</span>
        </div>
        <div className="hidden md:block text-muted tabular-nums">{clock}</div>
        <div className="flex items-center gap-1.5">
          <span
            className={`inline-block w-1.5 h-1.5 rounded-full ${
              apiUp == null
                ? "bg-dim"
                : apiUp
                ? "bg-up animate-led shadow-[0_0_6px_#0ecb81]"
                : "bg-down animate-led shadow-[0_0_6px_#f6465d]"
            }`}
          />
          <span className="microlabel">
            {apiUp == null ? "LINK" : apiUp ? "LIVE" : "DOWN"}
          </span>
        </div>
      </div>
    </header>
  );
}
