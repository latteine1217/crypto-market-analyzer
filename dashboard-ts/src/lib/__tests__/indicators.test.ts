import { describe, test, expect } from 'vitest'
import { calculateSMA, calculateRSI } from '../indicators'

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
})
