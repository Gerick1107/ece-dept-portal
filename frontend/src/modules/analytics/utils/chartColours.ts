/** Range-proportional blue → red palette (high-contrast, no pastel yellow). */
export const DIVERGING_PALETTE = [
  "#1a6fba",
  "#3a9bd5",
  "#56b8a6",
  "#74c476",
  "#d4a017",
  "#f07d00",
  "#e04020",
  "#c0001a",
] as const;

/** Evenly sample the palette for N discrete items (index 0 = blue, index N-1 = red). */
export function getColours(n: number, palette: readonly string[] = DIVERGING_PALETTE): string[] {
  if (n <= 0) return [];
  if (n === 1) return [palette[Math.floor(palette.length / 2)]];
  return Array.from({ length: n }, (_, i) =>
    palette[Math.round((i * (palette.length - 1)) / (n - 1))]
  );
}

/** Map a numeric value within [min, max] to a palette colour (low = blue, high = red). */
export function divergingColor(value: number, min = 0, max = 1): string {
  if (max <= min) return DIVERGING_PALETTE[Math.floor(DIVERGING_PALETTE.length / 2)];
  const t = Math.max(0, Math.min(1, (value - min) / (max - min)));
  const idx = Math.round(t * (DIVERGING_PALETTE.length - 1));
  return DIVERGING_PALETTE[idx];
}

export function divergingCellStyle(value: number, min: number, max: number): React.CSSProperties {
  const bg = divergingColor(value, min, max);
  const t = max > min ? (value - min) / (max - min) : 0.5;
  return {
    backgroundColor: bg,
    color: t < 0.25 || t > 0.75 ? "#fff" : "#1e293b",
  };
}

export const CHART_COLORS: string[] = [...DIVERGING_PALETTE];
