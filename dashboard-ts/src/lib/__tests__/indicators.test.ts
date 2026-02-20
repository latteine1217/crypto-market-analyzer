import { describe, test, expect } from 'vitest'
import { calculateSMA, calculateRSI, calculateFractals } from '../indicators'

describe('Technical Indicators', () => {
  test('calculateSMA returns correct moving average', () => {
    const data = [10, 20, 30, 40, 50]
    const sma = calculateSMA(data, 3)
    // index 0, 1 should be null
    expect(sma[0]).toBe(null)
    expect(sma[1]).toBe(null)
    // index 2: (10+20+30)/3 = 20
    expect(sma[2]).toBe(20)
    // index 3: (20+30+40)/3 = 30
    expect(sma[3]).toBe(30)
    // index 4: (30+40+50)/3 = 40
    expect(sma[4]).toBe(40)
  })
  
  test('calculateRSI handles basic calculation', () => {
    // 簡單的上升趨勢
    const data = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150]
    // period 14
    const rsi = calculateRSI(data, 14)
    // 只檢查最後一個是否有值且在合理範圍
    const lastRsi = rsi[rsi.length - 1]
    expect(lastRsi).not.toBeNull()
    expect(lastRsi).toBeGreaterThan(50)
    expect(lastRsi).toBeLessThanOrEqual(100)
  })

  test('calculateRSI handles edge cases', () => {
    const data = [100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100] // 無變化
    const rsi = calculateRSI(data, 14)
    expect(rsi[rsi.length - 1]).toBe(100) // avgLoss = 0 -> RSI = 100 (or handled as 50 depending on impl, my impl sets 100)
  })

  test('calculateRSI calculates correct initial value', () => {
    // Data: [0, 2, 1, 3, 2]
    // Changes: +2, -1, +2, -1
    // Period: 4
    // Gains: 2, 0, 2, 0 -> Sum 4. Avg 1.
    // Losses: 0, 1, 0, 1 -> Sum 2. Avg 0.5.
    // RS = 1 / 0.5 = 2.
    // RSI = 100 - (100 / (1 + 2)) = 66.67
    
    const data = [0, 2, 1, 3, 2]
    const rsi = calculateRSI(data, 4)
    const val = rsi[4]
    
    expect(val).not.toBeNull()
    expect(val).toBeCloseTo(66.67, 1)
  })

  test('calculateFractals finds classic up/down patterns', () => {
    const highs = [10, 12, 16, 13, 11, 12, 14, 13, 12]
    const lows = [8, 7, 6, 7, 8, 7, 5, 7, 8]
    const fractals = calculateFractals(highs, lows)

    expect(fractals.up[2]).toBe(true)
    expect(fractals.down[6]).toBe(true)
    expect(fractals.up[0]).toBe(false)
    expect(fractals.down[8]).toBe(false)
  })
})
