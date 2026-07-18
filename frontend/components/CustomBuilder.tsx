"use client";

export interface CustomSpec {
  indicators: {
    type: string;
    window?: number;
    fast?: number;
    slow?: number;
    signal?: number;
    col_name: string;
  }[];
  buy_query: string;
  sell_query: string;
}

export const DEFAULT_CUSTOM: CustomSpec = {
  indicators: [
    { type: "SMA", window: 20, col_name: "SMA20" },
    { type: "RSI", window: 14, col_name: "RSI14" },
  ],
  buy_query: "(close > SMA20) & (RSI14 < 40)",
  sell_query: "RSI14 > 70",
};

const IND_TYPES = ["SMA", "EMA", "RSI", "MACD"];

export function CustomBuilder({
  value,
  onChange,
}: {
  value: CustomSpec;
  onChange: (v: CustomSpec) => void;
}) {
  const addIndicator = () => {
    const n = value.indicators.length + 1;
    onChange({
      ...value,
      indicators: [
        ...value.indicators,
        { type: "SMA", window: 50, col_name: `SMA50_${n}` },
      ],
    });
  };

  const update = (i: number, patch: Partial<CustomSpec["indicators"][0]>) => {
    const inds = value.indicators.map((ind, j) =>
      j === i ? { ...ind, ...patch } : ind
    );
    onChange({ ...value, indicators: inds });
  };

  const remove = (i: number) =>
    onChange({
      ...value,
      indicators: value.indicators.filter((_, j) => j !== i),
    });

  return (
    <div className="mt-3 space-y-2 border border-line rounded-sm p-2 bg-panel2">
      <div className="flex justify-between items-center">
        <span className="microlabel">Indicators</span>
        <button className="text-amber text-xxs hover:underline" onClick={addIndicator}>
          + add
        </button>
      </div>
      {value.indicators.map((ind, i) => (
        <div key={i} className="flex gap-1.5 items-center">
          <select
            value={ind.type}
            onChange={(e) => {
              const t = e.target.value;
              update(i, {
                type: t,
                col_name: `${t}${ind.window ?? 14}_${i}`,
              });
            }}
            className="!w-20"
          >
            {IND_TYPES.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
          {ind.type !== "MACD" && (
            <input
              type="number"
              value={ind.window ?? 14}
              min={2}
              onChange={(e) =>
                update(i, {
                  window: Number(e.target.value),
                  col_name: `${ind.type}${e.target.value}_${i}`,
                })
              }
              className="!w-16"
            />
          )}
          <input
            type="text"
            value={ind.col_name}
            onChange={(e) => update(i, { col_name: e.target.value })}
            className="flex-1"
          />
          <button
            className="text-down text-xs px-1 hover:opacity-70"
            onClick={() => remove(i)}
          >
            ×
          </button>
        </div>
      ))}
      <div>
        <div className="microlabel mb-1 text-up">Buy When</div>
        <textarea
          rows={2}
          value={value.buy_query}
          onChange={(e) => onChange({ ...value, buy_query: e.target.value })}
          placeholder="(close > SMA20) & (RSI14 < 40)"
        />
      </div>
      <div>
        <div className="microlabel mb-1 text-down">Sell When</div>
        <textarea
          rows={2}
          value={value.sell_query}
          onChange={(e) => onChange({ ...value, sell_query: e.target.value })}
          placeholder="RSI14 > 70"
        />
      </div>
      <p className="text-micro text-dim font-sans">
        Pandas query syntax. Columns: open, high, low, close, volume + your
        indicator names.
      </p>
    </div>
  );
}
