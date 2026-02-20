import type { OHLCVData, OHLCVWithIndicators } from '@/types/market';

/**
 * 技術指標計算工具庫
 */

// Simple Moving Average (SMA) - 優化版本使用滑動窗口
export function calculateSMA(data: number[], period: number): (number | null)[] {
  // 輸入驗證
  if (data.length === 0 || period <= 0 || period > data.length) {
    return data.map(() => null);
  }

  const result: (number | null)[] = [];
  let sum = 0;
  
  for (let i = 0; i < data.length; i++) {
    sum += data[i];
    
    // 當窗口大小超過 period 時，移除最舊的數據
    if (i >= period) {
      sum -= data[i - period];
    }
    
    // 累積足夠數據後才開始輸出
    if (i >= period - 1) {
      result.push(sum / period);
    } else {
      result.push(null);
    }
  }
  
  return result;
}

// Exponential Moving Average (EMA)
export function calculateEMA(data: number[], period: number): (number | null)[] {
  const result: (number | null)[] = [];
  const multiplier = 2 / (period + 1);
  
  // 第一個 EMA 使用 SMA
  let ema = data.slice(0, period).reduce((a, b) => a + b, 0) / period;
  
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      result.push(null);
    } else if (i === period - 1) {
      result.push(ema);
    } else {
      ema = (data[i] - ema) * multiplier + ema;
      result.push(ema);
    }
  }
  
  return result;
}

// Relative Strength Index (RSI) - 優化版本 O(N)
export function calculateRSI(data: number[], period: number = 14): (number | null)[] {
  if (data.length <= period) {
    return data.map(() => null);
  }

  const result: (number | null)[] = [];
  let avgGain = 0;
  let avgLoss = 0;

  for (let i = 0; i < data.length; i++) {
    if (i === 0) {
      result.push(null);
      continue;
    }

    const change = data[i] - data[i - 1];
    const gain = Math.max(0, change);
    const loss = Math.max(0, -change);

    if (i < period) {
      avgGain += gain;
      avgLoss += loss;
      result.push(null);
    } else if (i === period) {
      // Add current period's gain/loss to the sum
      avgGain += gain;
      avgLoss += loss;

      // 第一個 RSI 使用簡單平均
      avgGain = avgGain / period;
      avgLoss = avgLoss / period;
      
      const rsi = avgLoss === 0 ? 100 : (100 - 100 / (1 + avgGain / avgLoss));
      result.push(rsi);
    } else {
      // 後續使用 Wilder's Smoothing: (prevAvg * 13 + current) / 14
      avgGain = (avgGain * (period - 1) + gain) / period;
      avgLoss = (avgLoss * (period - 1) + loss) / period;
      
      const rsi = avgLoss === 0 ? 100 : (100 - 100 / (1 + avgGain / avgLoss));
      result.push(rsi);
    }
  }

  return result;
}

// MACD (Moving Average Convergence Divergence)
export function calculateMACD(
  data: number[],
  fastPeriod: number = 12,
  slowPeriod: number = 26,
  signalPeriod: number = 9
): {
  macd: (number | null)[];
  signal: (number | null)[];
  histogram: (number | null)[];
} {
  const emaFast = calculateEMA(data, fastPeriod);
  const emaSlow = calculateEMA(data, slowPeriod);
  
  const macd: (number | null)[] = emaFast.map((fast, i) => {
    const slow = emaSlow[i];
    if (fast === null || slow === null) return null;
    return fast - slow;
  });
  
  const macdValues = macd.filter(v => v !== null) as number[];
  const signalEMA = calculateEMA(macdValues, signalPeriod);
  
  const signal: (number | null)[] = [];
  let signalIndex = 0;
  
  for (let i = 0; i < macd.length; i++) {
    if (macd[i] === null) {
      signal.push(null);
    } else {
      signal.push(signalEMA[signalIndex] || null);
      signalIndex++;
    }
  }
  
  const histogram = macd.map((m, i) => {
    const s = signal[i];
    if (m === null || s === null) return null;
    return m - s;
  });
  
  return { macd, signal, histogram };
}

// Bollinger Bands - 優化版本 O(N)
export function calculateBollingerBands(
  data: number[],
  period: number = 20,
  stdDevMultiplier: number = 2
): {
  upper: (number | null)[];
  middle: (number | null)[];
  lower: (number | null)[];
} {
  const result = {
    upper: [] as (number | null)[],
    middle: [] as (number | null)[],
    lower: [] as (number | null)[],
  };

  let sum = 0;
  let sumSq = 0;

  for (let i = 0; i < data.length; i++) {
    const val = data[i];
    sum += val;
    sumSq += val * val;

    if (i >= period) {
      const oldVal = data[i - period];
      sum -= oldVal;
      sumSq -= oldVal * oldVal;
    }

    if (i >= period - 1) {
      const mean = sum / period;
      // 變異數公式: E[X^2] - (E[X])^2
      const variance = Math.max(0, (sumSq / period) - (mean * mean));
      const stdDev = Math.sqrt(variance);

      result.middle.push(mean);
      result.upper.push(mean + stdDev * stdDevMultiplier);
      result.lower.push(mean - stdDev * stdDevMultiplier);
    } else {
      result.middle.push(null);
      result.upper.push(null);
      result.lower.push(null);
    }
  }

  return result;
}

// Williams Fractal
export function calculateFractals(
  highs: number[],
  lows: number[],
  period: number = 5
): {
  up: boolean[];
  down: boolean[];
} {
  const up: boolean[] = [];
  const down: boolean[] = [];
  const halfWindow = Math.max(1, Math.floor(period / 2));
  
  for (let i = 0; i < highs.length; i++) {
    if (i >= halfWindow && i < highs.length - halfWindow) {
      let isUp = true;
      let isDown = true;

      for (let offset = 1; offset <= halfWindow; offset++) {
        if (!(highs[i] > highs[i - offset] && highs[i] > highs[i + offset])) {
          isUp = false;
        }
        if (!(lows[i] < lows[i - offset] && lows[i] < lows[i + offset])) {
          isDown = false;
        }
        if (!isUp && !isDown) break;
      }

      up.push(isUp);
      down.push(isDown);
    } else {
      up.push(false);
      down.push(false);
    }
  }
  
  return { up, down };
}

// 計算所有指標
export function calculateAllIndicators(data: OHLCVData[]): OHLCVWithIndicators[] {
  if (data.length === 0) return [];
  
  const closes = data.map(d => Number(d.close));
  const highs = data.map(d => Number(d.high));
  const lows = data.map(d => Number(d.low));
  
  const sma20 = calculateSMA(closes, 20);
  const sma50 = calculateSMA(closes, 50);
  const sma60 = calculateSMA(closes, 60);
  const sma200 = calculateSMA(closes, 200);
  const rsi14 = calculateRSI(closes, 14);
  const { macd, signal: macdSignal, histogram: macdHist } = calculateMACD(closes);
  const { upper: bbUpper, middle: bbMiddle, lower: bbLower } = calculateBollingerBands(closes);
  const fractals = calculateFractals(highs, lows, 12);
  
  return data.map((d, i) => ({
    ...d,
    sma_20: sma20[i] || undefined,
    sma_50: sma50[i] || undefined,
    sma_60: sma60[i] || undefined,
    sma_200: sma200[i] || undefined,
    rsi_14: rsi14[i] || undefined,
    macd: macd[i] || undefined,
    macd_signal: macdSignal[i] || undefined,
    macd_hist: macdHist[i] || undefined,
    bollinger_upper: bbUpper[i] || undefined,
    bollinger_middle: bbMiddle[i] || undefined,
    bollinger_lower: bbLower[i] || undefined,
    fractal_up: fractals.up[i],
    fractal_down: fractals.down[i],
  }));
}
