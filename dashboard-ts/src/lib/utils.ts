import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(num: number | null | undefined, decimals: number = 2): string {
  if (num === null || num === undefined || !Number.isFinite(num)) {
    return '--';
  }
  return num.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function formatPrice(price: number | null | undefined): string {
  if (price === null || price === undefined || !Number.isFinite(price)) {
    return '--';
  }
  if (price >= 1000) {
    return formatNumber(price, 2);
  } else if (price >= 1) {
    return formatNumber(price, 4);
  } else {
    return formatNumber(price, 6);
  }
}

export function formatPercent(percent: number | null | undefined): string {
  if (percent === null || percent === undefined || !Number.isFinite(percent)) {
    return '--';
  }
  const sign = percent >= 0 ? '+' : '';
  return `${sign}${formatNumber(percent, 2)}%`;
}

export function formatVolume(volume: number | null | undefined): string {
  if (volume === null || volume === undefined || !Number.isFinite(volume)) {
    return '--';
  }
  if (volume >= 1_000_000) {
    return `${formatNumber(volume / 1_000_000, 2)}M`;
  } else if (volume >= 1_000) {
    return `${formatNumber(volume / 1_000, 2)}K`;
  }
  return formatNumber(volume, 2);
}
