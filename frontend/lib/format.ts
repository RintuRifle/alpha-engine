export const fmtPct = (v: number | null | undefined, dp = 2) =>
  v == null ? "—" : `${(v * 100).toFixed(dp)}%`;

export const fmtNum = (v: number | null | undefined, dp = 2) =>
  v == null ? "—" : v.toFixed(dp);

export const fmtMoney = (v: number | null | undefined) =>
  v == null
    ? "—"
    : v.toLocaleString("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 0,
      });

export const fmtCompact = (v: number | null | undefined) =>
  v == null
    ? "—"
    : Intl.NumberFormat("en-US", { notation: "compact" }).format(v);

export const signColor = (v: number | null | undefined) =>
  v == null ? "text-muted" : v >= 0 ? "text-up" : "text-down";

export const MONTHS = [
  "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
  "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
];

export function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

export function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

/** Build an inclusive numeric range for optimizer grids. */
export function buildRange(min: number, max: number, step: number): number[] {
  const out: number[] = [];
  const isFloat = !Number.isInteger(step) || !Number.isInteger(min);
  for (let v = min; v <= max + 1e-9; v += step) {
    out.push(isFloat ? parseFloat(v.toFixed(4)) : Math.round(v));
    if (out.length > 200) break;
  }
  return out;
}
