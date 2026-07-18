"use client";

import { useState } from "react";
import type { StrategySchema, BacktestConfig, ExecutionConfig } from "@/lib/api";
import { CustomBuilder, type CustomSpec } from "./CustomBuilder";

export const DEFAULT_EXECUTION: ExecutionConfig = {
  spread_bps: 0,
  slippage_model: "fixed",
  slippage_bps: 5,
  vol_coef: 0.1,
  impact_bps: 10,
  max_participation: 1.0,
  short_margin_pct: 1.0,
};

export interface ConfigState {
  ticker: string;
  start_date: string;
  end_date: string;
  interval: string;
  intraday_square_off: boolean;
  data_source: string;
  execution: ExecutionConfig;
  capital: number;
  allocation: number;
  benchmark: string;
  strategy: string;
  params: Record<string, number>;
  custom: CustomSpec;
  allow_short: boolean;
  use_stops: boolean;
  atr_multiplier: number;
  use_trailing_stop: boolean;
  use_circuit_breaker: boolean;
  regime_gate: boolean;
  stress_test: boolean;
}

// Yahoo Finance intraday history limits (calendar days back from today)
export const INTERVAL_LIMITS: Record<string, number | null> = {
  "1m": 7,
  "5m": 60,
  "15m": 60,
  "30m": 60,
  "1h": 730,
  "1d": null,
};

const INTERVALS = ["1m", "5m", "15m", "30m", "1h", "1d"];

export function clampStartForInterval(
  interval: string,
  start: string
): string {
  const limit = INTERVAL_LIMITS[interval];
  if (limit == null) return start;
  const min = new Date();
  min.setDate(min.getDate() - (limit - 1));
  const minIso = min.toISOString().slice(0, 10);
  return start < minIso ? minIso : start;
}

export function toBacktestRequest(c: ConfigState): BacktestConfig {
  return {
    ticker: c.ticker,
    start_date: c.start_date,
    end_date: c.end_date,
    interval: c.interval,
    intraday_square_off: c.intraday_square_off,
    data_source: c.data_source,
    execution: c.execution,
    strategy: c.strategy,
    params: c.params,
    custom: c.strategy === "custom" ? c.custom : undefined,
    capital: c.capital,
    allocation: c.allocation,
    benchmark: c.benchmark,
    allow_short: c.allow_short,
    use_stops: c.use_stops,
    atr_multiplier: c.atr_multiplier,
    use_trailing_stop: c.use_trailing_stop,
    use_circuit_breaker: c.use_circuit_breaker,
    regime_gate: c.regime_gate,
    stress_test: c.stress_test,
  };
}

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className="flex items-center justify-between w-full py-1 group"
    >
      <span className="text-xxs text-muted group-hover:text-text transition-colors">
        {label}
      </span>
      <span
        className={`w-7 h-3.5 rounded-full relative transition-colors duration-150 ${
          checked ? "bg-amber/80" : "bg-line"
        }`}
      >
        <span
          className={`absolute top-0.5 w-2.5 h-2.5 rounded-full bg-bg transition-all duration-150 ${
            checked ? "left-4" : "left-0.5"
          }`}
        />
      </span>
    </button>
  );
}

export function ConfigPanel({
  strategies,
  config,
  setConfig,
  running,
  onRun,
  onCompare,
}: {
  strategies: StrategySchema[];
  config: ConfigState;
  setConfig: (updater: (c: ConfigState) => ConfigState) => void;
  running: boolean;
  onRun: () => void;
  onCompare: () => void;
}) {
  const [showRisk, setShowRisk] = useState(false);
  const [showExec, setShowExec] = useState(false);
  const strat = strategies.find((s) => s.key === config.strategy);

  const set = <K extends keyof ConfigState>(k: K, v: ConfigState[K]) =>
    setConfig((c) => ({ ...c, [k]: v }));

  const setExec = <K extends keyof ConfigState["execution"]>(
    k: K,
    v: ConfigState["execution"][K]
  ) =>
    setConfig((c) => ({ ...c, execution: { ...c.execution, [k]: v } }));

  return (
    <aside className="w-[290px] shrink-0 border-r border-line bg-panel overflow-y-auto flex flex-col">
      <div className="p-3 space-y-4 flex-1">
        {/* Instrument */}
        <div>
          <div className="microlabel mb-2">Instrument</div>
          <input
            type="text"
            value={config.ticker}
            onChange={(e) => set("ticker", e.target.value.toUpperCase())}
            placeholder="TICKER (e.g. AAPL, RELIANCE.NS)"
            className="font-semibold tracking-wider"
          />

          {/* Timeframe */}
          <div className="microlabel mt-3 mb-1.5">Timeframe</div>
          <div className="grid grid-cols-6 gap-px bg-line border border-line rounded-sm overflow-hidden">
            {INTERVALS.map((iv) => (
              <button
                key={iv}
                onClick={() =>
                  setConfig((c) => ({
                    ...c,
                    interval: iv,
                    start_date: clampStartForInterval(iv, c.start_date),
                    intraday_square_off:
                      iv === "1d" ? false : c.intraday_square_off,
                  }))
                }
                className={`py-1.5 text-micro font-mono uppercase transition-colors ${
                  config.interval === iv
                    ? "bg-amber text-black font-bold"
                    : "bg-panel2 text-muted hover:text-text"
                }`}
              >
                {iv}
              </button>
            ))}
          </div>
          {config.interval !== "1d" && (
            <p className="text-micro text-dim mt-1 font-sans">
              Yahoo serves ~{INTERVAL_LIMITS[config.interval]}d of{" "}
              {config.interval} history. Alpaca (US equities) serves years —
              set data source below.
            </p>
          )}

          {/* Data source */}
          <div className="grid grid-cols-2 gap-2 mt-2">
            <div>
              <div className="microlabel mb-1">Data Source</div>
              <select
                value={config.data_source}
                onChange={(e) => set("data_source", e.target.value)}
              >
                <option value="auto">Auto</option>
                <option value="yahoo">Yahoo</option>
                <option value="alpaca">Alpaca</option>
              </select>
            </div>
            <div className="self-end">
              <p className="text-micro text-dim font-sans leading-tight pb-1">
                Auto: Alpaca for long intraday ranges (needs keys on backend)
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 mt-2">
            <div>
              <div className="microlabel mb-1">From</div>
              <input
                type="date"
                value={config.start_date}
                onChange={(e) => set("start_date", e.target.value)}
              />
            </div>
            <div>
              <div className="microlabel mb-1">To</div>
              <input
                type="date"
                value={config.end_date}
                onChange={(e) => set("end_date", e.target.value)}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2 mt-2">
            <div>
              <div className="microlabel mb-1">Capital $</div>
              <input
                type="number"
                value={config.capital}
                min={1000}
                step={1000}
                onChange={(e) => set("capital", Number(e.target.value))}
              />
            </div>
            <div>
              <div className="microlabel mb-1">Benchmark</div>
              <input
                type="text"
                value={config.benchmark}
                onChange={(e) => set("benchmark", e.target.value.toUpperCase())}
              />
            </div>
          </div>
        </div>

        {/* Strategy */}
        <div>
          <div className="microlabel mb-2">Strategy</div>
          <select
            value={config.strategy}
            onChange={(e) => {
              const key = e.target.value;
              const s = strategies.find((x) => x.key === key);
              const defaults: Record<string, number> = {};
              s?.params.forEach((p) => (defaults[p.name] = p.default));
              setConfig((c) => ({ ...c, strategy: key, params: defaults }));
            }}
          >
            {strategies.map((s) => (
              <option key={s.key} value={s.key}>
                {s.label}
              </option>
            ))}
          </select>
          {strat && (
            <p className="text-micro text-dim mt-1.5 font-sans leading-relaxed">
              {strat.description}
            </p>
          )}

          {/* Dynamic params */}
          {strat && strat.params.length > 0 && (
            <div className="mt-3 space-y-3">
              {strat.params.map((p) => (
                <div key={p.name}>
                  <div className="flex justify-between items-baseline mb-1">
                    <span className="text-xxs text-muted">{p.label}</span>
                    <span className="text-xxs text-amber tabular-nums font-semibold">
                      {config.params[p.name] ?? p.default}
                    </span>
                  </div>
                  <input
                    type="range"
                    min={p.min}
                    max={p.max}
                    step={p.step}
                    value={config.params[p.name] ?? p.default}
                    onChange={(e) =>
                      setConfig((c) => ({
                        ...c,
                        params: {
                          ...c.params,
                          [p.name]: Number(e.target.value),
                        },
                      }))
                    }
                    className="w-full"
                  />
                </div>
              ))}
            </div>
          )}

          {config.strategy === "custom" && (
            <CustomBuilder
              value={config.custom}
              onChange={(custom) => setConfig((c) => ({ ...c, custom }))}
            />
          )}
        </div>

        {/* Execution model */}
        <div className="border-t border-line pt-3">
          <button
            className="microlabel w-full text-left flex justify-between items-center"
            onClick={() => setShowExec((v) => !v)}
          >
            <span>Execution Model</span>
            <span className="text-dim">{showExec ? "−" : "+"}</span>
          </button>
          {showExec && (
            <div className="mt-2 space-y-2.5">
              <div>
                <div className="flex justify-between items-baseline mb-1">
                  <span className="text-xxs text-muted">Bid-Ask Spread</span>
                  <span className="text-xxs text-amber tabular-nums">
                    {config.execution.spread_bps} bps
                  </span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={50}
                  step={1}
                  value={config.execution.spread_bps}
                  onChange={(e) => setExec("spread_bps", Number(e.target.value))}
                  className="w-full"
                />
              </div>

              <div>
                <div className="microlabel mb-1">Slippage Model</div>
                <select
                  value={config.execution.slippage_model}
                  onChange={(e) =>
                    setExec(
                      "slippage_model",
                      e.target.value as ConfigState["execution"]["slippage_model"]
                    )
                  }
                >
                  <option value="fixed">Fixed (bps)</option>
                  <option value="volatility">Volatility-scaled</option>
                  <option value="volume">Volume impact (√)</option>
                </select>
              </div>

              {config.execution.slippage_model === "fixed" && (
                <div>
                  <div className="flex justify-between items-baseline mb-1">
                    <span className="text-xxs text-muted">Slippage</span>
                    <span className="text-xxs text-amber tabular-nums">
                      {config.execution.slippage_bps} bps
                    </span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={50}
                    step={1}
                    value={config.execution.slippage_bps}
                    onChange={(e) =>
                      setExec("slippage_bps", Number(e.target.value))
                    }
                    className="w-full"
                  />
                </div>
              )}
              {config.execution.slippage_model === "volatility" && (
                <div>
                  <div className="flex justify-between items-baseline mb-1">
                    <span className="text-xxs text-muted">
                      Bar-Range Fraction
                    </span>
                    <span className="text-xxs text-amber tabular-nums">
                      {(config.execution.vol_coef * 100).toFixed(0)}%
                    </span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={0.5}
                    step={0.05}
                    value={config.execution.vol_coef}
                    onChange={(e) => setExec("vol_coef", Number(e.target.value))}
                    className="w-full"
                  />
                </div>
              )}
              {config.execution.slippage_model === "volume" && (
                <div>
                  <div className="flex justify-between items-baseline mb-1">
                    <span className="text-xxs text-muted">
                      Impact @ 100% part.
                    </span>
                    <span className="text-xxs text-amber tabular-nums">
                      {config.execution.impact_bps} bps
                    </span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={100}
                    step={5}
                    value={config.execution.impact_bps}
                    onChange={(e) =>
                      setExec("impact_bps", Number(e.target.value))
                    }
                    className="w-full"
                  />
                </div>
              )}

              <div>
                <div className="flex justify-between items-baseline mb-1">
                  <span className="text-xxs text-muted">
                    Max Volume Participation
                  </span>
                  <span className="text-xxs text-amber tabular-nums">
                    {config.execution.max_participation >= 1
                      ? "∞"
                      : `${(config.execution.max_participation * 100).toFixed(0)}%`}
                  </span>
                </div>
                <input
                  type="range"
                  min={0.01}
                  max={1}
                  step={0.01}
                  value={config.execution.max_participation}
                  onChange={(e) =>
                    setExec("max_participation", Number(e.target.value))
                  }
                  className="w-full"
                />
                <p className="text-micro text-dim font-sans">
                  Orders above this % of bar volume get partially filled.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Risk controls */}
        <div className="border-t border-line pt-3">
          <button
            className="microlabel w-full text-left flex justify-between items-center"
            onClick={() => setShowRisk((v) => !v)}
          >
            <span>Risk Controls</span>
            <span className="text-dim">{showRisk ? "−" : "+"}</span>
          </button>
          {showRisk && (
            <div className="mt-2 space-y-1">
              {config.interval !== "1d" && (
                <Toggle
                  label="Intraday Square-Off (EOD flat)"
                  checked={config.intraday_square_off}
                  onChange={(v) => set("intraday_square_off", v)}
                />
              )}
              <Toggle
                label="ATR Stop Losses"
                checked={config.use_stops}
                onChange={(v) => set("use_stops", v)}
              />
              {config.use_stops && (
                <div className="pl-2 py-1">
                  <div className="flex justify-between items-baseline mb-1">
                    <span className="text-xxs text-muted">ATR Multiplier</span>
                    <span className="text-xxs text-amber tabular-nums">
                      {config.atr_multiplier.toFixed(1)}x
                    </span>
                  </div>
                  <input
                    type="range"
                    min={1}
                    max={4}
                    step={0.5}
                    value={config.atr_multiplier}
                    onChange={(e) =>
                      set("atr_multiplier", Number(e.target.value))
                    }
                    className="w-full"
                  />
                  <Toggle
                    label="Trailing Stop"
                    checked={config.use_trailing_stop}
                    onChange={(v) => set("use_trailing_stop", v)}
                  />
                </div>
              )}
              <Toggle
                label="Circuit Breaker (-3%)"
                checked={config.use_circuit_breaker}
                onChange={(v) => set("use_circuit_breaker", v)}
              />
              <Toggle
                label="Allow Short Selling"
                checked={config.allow_short}
                onChange={(v) => set("allow_short", v)}
              />
              <Toggle
                label="Regime Signal Gating"
                checked={config.regime_gate}
                onChange={(v) => set("regime_gate", v)}
              />
              <Toggle
                label="Monte Carlo Stress Test"
                checked={config.stress_test}
                onChange={(v) => set("stress_test", v)}
              />
              <div className="pt-1">
                <div className="flex justify-between items-baseline mb-1">
                  <span className="text-xxs text-muted">Allocation</span>
                  <span className="text-xxs text-amber tabular-nums">
                    {(config.allocation * 100).toFixed(0)}%
                  </span>
                </div>
                <input
                  type="range"
                  min={0.1}
                  max={1}
                  step={0.05}
                  value={config.allocation}
                  onChange={(e) => set("allocation", Number(e.target.value))}
                  className="w-full"
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="p-3 border-t border-line bg-panel2 sticky bottom-0 space-y-2">
        <button
          className="btn-primary w-full"
          disabled={running || !config.ticker}
          onClick={onRun}
        >
          {running ? "Running..." : "▸ Run Backtest"}
        </button>
        <button
          className="btn-ghost w-full"
          disabled={running || !config.ticker}
          onClick={onCompare}
        >
          Compare All Strategies
        </button>
      </div>
    </aside>
  );
}
