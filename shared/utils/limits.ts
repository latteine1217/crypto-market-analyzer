export const clampLimit = (
  rawValue: any,
  options: { min?: number; max?: number; defaultValue: number }
): number => {
  const { min = 1, max, defaultValue } = options;
  const parsed = parseInt(String(rawValue), 10);
  const value = Number.isFinite(parsed) ? parsed : defaultValue;
  const clampedMin = Math.max(value, min);
  if (max !== undefined) {
    return Math.min(clampedMin, max);
  }
  return clampedMin;
};
