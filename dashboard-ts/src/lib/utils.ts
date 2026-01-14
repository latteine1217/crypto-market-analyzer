import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(num: number, decimals: number = 2): string {
  return num.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function formatPrice(price: number): string {
  if (price >= 1000) {
    return formatNumber(price, 2);
  } else if (price >= 1) {
    return formatNumber(price, 4);
  } else {
    return formatNumber(price, 6);
  }
}

export function formatPercent(percent: number): string {
  const sign = percent >= 0 ? '+' : '';
  return `${sign}${formatNumber(percent, 2)}%`;
}

export function formatVolume(volume: number): string {
  if (volume >= 1_000_000) {
    return `${formatNumber(volume / 1_000_000, 2)}M`;
  } else if (volume >= 1_000) {
    return `${formatNumber(volume / 1_000, 2)}K`;
  }
  return formatNumber(volume, 2);
}
