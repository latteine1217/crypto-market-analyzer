'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { 
  createChart, 
  createSeriesMarkers,
  ColorType,
  CandlestickSeries,
  LineSeries,
  AreaSeries,
  HistogramSeries,
  PriceScaleMode,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
  type Time,
  type CandlestickData,
  type LineData,
  type HistogramData,
  type AreaData,
  type SeriesMarker,
  type ISeriesMarkersPluginApi
} from 'lightweight-charts'
import type { OHLCVWithIndicators } from '@/types/market'

interface CVDPoint {
  time: string | number
  cvd: number
}

interface LiquidationData {
  timestamp: string | number
  side: 'buy' | 'sell' | 'long_liquidated' | 'short_liquidated'
  price: number
  value_usd: number
}

interface Props {
  data: OHLCVWithIndicators[]
  cvdData?: CVDPoint[]
  liquidations?: LiquidationData[]
  visibleIndicators?: {
    ma20: boolean
    ma60: boolean
    ma200: boolean
    bb: boolean
    fractal: boolean
    vpvr: boolean
  }
  onChartCreate?: (chart: IChartApi) => void
  timeframe?: string
  key?: string // 用於識別參數變化，觸發重新首次載入
}

interface VolumeProfileRow {
  lower: number
  upper: number
  volume: number
  ratio: number
}

interface PocBand {
  topPx: number
  heightPx: number
  centerPx: number
}

interface PocPriceRange {
  lower: number
  upper: number
  center: number
}

const formatTickLabel = (time: Time, timeframe: string) => {
  const timestampMs = typeof time === 'number'
    ? time * 1000
    : (typeof time === 'string'
      ? Date.parse(time)
      : new Date(time.year, time.month - 1, time.day).getTime())

  const date = new Date(timestampMs)
  if (Number.isNaN(date.getTime())) return ''

  if (timeframe === '1d') {
    return date.toLocaleDateString('en-US', { month: '2-digit', day: '2-digit' })
  }
  if (timeframe === '4h' || timeframe === '1h') {
    return date.toLocaleString('en-US', { month: '2-digit', day: '2-digit', hour: '2-digit', hour12: false })
  }
  return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
}

const toUnixSeconds = (time: Time): number | null => {
  if (typeof time === 'number') return Math.floor(time)
  if (typeof time === 'string') {
    const ms = Date.parse(time)
    return Number.isFinite(ms) ? Math.floor(ms / 1000) : null
  }
  const ms = Date.UTC(time.year, time.month - 1, time.day, 0, 0, 0, 0)
  return Number.isFinite(ms) ? Math.floor(ms / 1000) : null
}

export function LightweightCandlestickChart({ 
  data, 
  cvdData = [],
  liquidations = [],
  visibleIndicators = { ma20: true, ma60: true, ma200: true, bb: false, fractal: false, vpvr: false },
  onChartCreate,
  timeframe = '1h',
  key
}: Props) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<any>(null) // 使用 any 繞過嚴格的 v4 類型檢查，確保編譯通過
  const markersPluginRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null)
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)
  const cvdSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const ma20SeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const ma60SeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const ma200SeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const bbUpperSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const bbLowerSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const isFirstLoadRef = useRef(true) // 追蹤是否為首次載入
  const previousKeyRef = useRef(key) // 追蹤 key 變化
  const candleMetaRef = useRef<Array<{ time: number; high: number; low: number; volume: number }>>([])
  const vpvrEnabledRef = useRef(visibleIndicators.vpvr)
  const followLatestRef = useRef(true)
  const [volumeProfile, setVolumeProfile] = useState<VolumeProfileRow[]>([])
  const [volumeProfileTotal, setVolumeProfileTotal] = useState(0)
  const [pocPriceRange, setPocPriceRange] = useState<PocPriceRange | null>(null)
  const [pocBand, setPocBand] = useState<PocBand | null>(null)

  // 當 key 變化時（例如切換 timeframe/symbol），重置為首次載入
  useEffect(() => {
    if (key !== previousKeyRef.current) {
      isFirstLoadRef.current = true
      previousKeyRef.current = key
    }
  }, [key])

  useEffect(() => {
    vpvrEnabledRef.current = visibleIndicators.vpvr
    if (!visibleIndicators.vpvr) {
      setVolumeProfile([])
      setVolumeProfileTotal(0)
      setPocPriceRange(null)
      setPocBand(null)
    }
  }, [visibleIndicators.vpvr])

  const updatePocBandFromRows = useCallback((rows: VolumeProfileRow[]) => {
    if (rows.length === 0) {
      setPocPriceRange(null)
      setPocBand(null)
      return
    }
    const poc = rows.reduce((best, row) => (row.volume > best.volume ? row : best), rows[0])
    setPocPriceRange({
      lower: poc.lower,
      upper: poc.upper,
      center: (poc.upper + poc.lower) / 2,
    })
  }, [])

  const buildVolumeProfileFromRange = useCallback((fromSec: number, toSec: number) => {
    const points = candleMetaRef.current
    if (!vpvrEnabledRef.current || points.length === 0) {
      setVolumeProfile([])
      setVolumeProfileTotal(0)
      setPocBand(null)
      return
    }

    const startSec = Math.min(fromSec, toSec)
    const endSec = Math.max(fromSec, toSec)
    const visible = points.filter(p => p.time >= startSec && p.time <= endSec)
    if (visible.length === 0) {
      setVolumeProfile([])
      setVolumeProfileTotal(0)
      setPocBand(null)
      return
    }

    const minPrice = Math.min(...visible.map(p => p.low))
    const maxPrice = Math.max(...visible.map(p => p.high))
    if (!Number.isFinite(minPrice) || !Number.isFinite(maxPrice)) {
      setVolumeProfile([])
      setVolumeProfileTotal(0)
      setPocBand(null)
      return
    }

    const bins = 30
    const span = Math.max(maxPrice - minPrice, Number.EPSILON)
    const bucketSize = span / bins
    const bucketVolumes = new Array(bins).fill(0) as number[]

    for (const p of visible) {
      const candleSpan = Math.max(p.high - p.low, Number.EPSILON)
      const start = Math.max(0, Math.floor((p.low - minPrice) / bucketSize))
      const end = Math.min(bins - 1, Math.floor((p.high - minPrice) / bucketSize))
      const touched = Math.max(1, end - start + 1)
      const perBucketVolume = p.volume / touched

      if (candleSpan <= Number.EPSILON) {
        const idx = Math.min(bins - 1, Math.max(0, Math.floor((p.high - minPrice) / bucketSize)))
        bucketVolumes[idx] += p.volume
        continue
      }

      for (let idx = start; idx <= end; idx++) {
        bucketVolumes[idx] += perBucketVolume
      }
    }

    const maxVolume = Math.max(...bucketVolumes, 0)
    const total = bucketVolumes.reduce((acc, v) => acc + v, 0)
    const rows: VolumeProfileRow[] = bucketVolumes.map((v, idx) => {
      const lower = minPrice + idx * bucketSize
      const upper = idx === bins - 1 ? maxPrice : lower + bucketSize
      return {
        lower,
        upper,
        volume: v,
        ratio: maxVolume > 0 ? v / maxVolume : 0,
      }
    }).filter(r => r.volume > 0)

    rows.sort((a, b) => b.upper - a.upper)
    setVolumeProfile(rows)
    setVolumeProfileTotal(total)
    updatePocBandFromRows(rows)
  }, [updatePocBandFromRows])

  const buildVolumeProfileFromLogicalRange = useCallback((fromLogical: number, toLogical: number) => {
    const points = candleMetaRef.current
    if (!vpvrEnabledRef.current || points.length === 0) {
      setVolumeProfile([])
      setVolumeProfileTotal(0)
      setPocPriceRange(null)
      setPocBand(null)
      return
    }

    const start = Math.max(0, Math.floor(Math.min(fromLogical, toLogical)))
    const end = Math.min(points.length - 1, Math.ceil(Math.max(fromLogical, toLogical)))
    if (start > end) {
      setVolumeProfile([])
      setVolumeProfileTotal(0)
      setPocPriceRange(null)
      setPocBand(null)
      return
    }

    const sliced = points.slice(start, end + 1)
    if (sliced.length === 0) {
      setVolumeProfile([])
      setVolumeProfileTotal(0)
      setPocPriceRange(null)
      setPocBand(null)
      return
    }

    const minPrice = Math.min(...sliced.map(p => p.low))
    const maxPrice = Math.max(...sliced.map(p => p.high))
    if (!Number.isFinite(minPrice) || !Number.isFinite(maxPrice)) {
      setVolumeProfile([])
      setVolumeProfileTotal(0)
      setPocBand(null)
      return
    }

    const bins = 30
    const span = Math.max(maxPrice - minPrice, Number.EPSILON)
    const bucketSize = span / bins
    const bucketVolumes = new Array(bins).fill(0) as number[]

    for (const p of sliced) {
      const startIdx = Math.max(0, Math.floor((p.low - minPrice) / bucketSize))
      const endIdx = Math.min(bins - 1, Math.floor((p.high - minPrice) / bucketSize))
      const touched = Math.max(1, endIdx - startIdx + 1)
      const perBucketVolume = p.volume / touched
      for (let idx = startIdx; idx <= endIdx; idx++) {
        bucketVolumes[idx] += perBucketVolume
      }
    }

    const maxVolume = Math.max(...bucketVolumes, 0)
    const total = bucketVolumes.reduce((acc, v) => acc + v, 0)
    const rows: VolumeProfileRow[] = bucketVolumes
      .map((v, idx) => {
        const lower = minPrice + idx * bucketSize
        const upper = idx === bins - 1 ? maxPrice : lower + bucketSize
        return { lower, upper, volume: v, ratio: maxVolume > 0 ? v / maxVolume : 0 }
      })
      .filter(r => r.volume > 0)
      .sort((a, b) => b.upper - a.upper)

    setVolumeProfile(rows)
    setVolumeProfileTotal(total)
    updatePocBandFromRows(rows)
  }, [updatePocBandFromRows])

  useEffect(() => {
    if (!chartContainerRef.current) return

    // 創建圖表
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#111827' },
        textColor: '#9ca3af',
      },
      grid: {
        vertLines: { color: '#374151' },
        horzLines: { color: '#374151' },
      },
      width: chartContainerRef.current.clientWidth,
      height: 500,
      rightPriceScale: {
        borderColor: '#374151',
        mode: PriceScaleMode.Logarithmic,
        scaleMargins: {
          top: 0.1,
          bottom: 0.2,
        },
      },
      timeScale: {
        borderColor: '#374151',
        timeVisible: true,
        secondsVisible: false,
        tickMarkFormatter: (time: Time) => formatTickLabel(time, timeframe),
      },
      crosshair: {
        mode: 1,
      },
    })

    chartRef.current = chart
    if (onChartCreate) onChartCreate(chart)

    // 1. 創建 K 線序列
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderUpColor: '#22c55e',
      borderDownColor: '#ef4444',
      wickUpColor: '#22c55e',
      wickDownColor: '#ef4444',
    })
    candleSeriesRef.current = candleSeries
    markersPluginRef.current = createSeriesMarkers(candleSeries, [])

    // 2. 成交量
    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: '#26a69a',
      priceFormat: { type: 'volume' },
      priceScaleId: '', // Overlay
    });
    
    chart.priceScale('').applyOptions({
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    });
    volumeSeriesRef.current = volumeSeries;

    // 2.5 CVD 序列 (獨立座標軸)
    const cvdSeries = chart.addSeries(LineSeries, {
      color: 'rgba(0, 227, 150, 0.8)',
      lineWidth: 2,
      priceScaleId: 'cvd', // 使用獨立座標軸
      title: 'CVD',
    });
    
    chart.priceScale('cvd').applyOptions({
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
      visible: false, // 隱藏數值軸以保持簡潔
    });
    cvdSeriesRef.current = cvdSeries;

    // 3. 其他指標 (MA, BB)
    const ma20Series = chart.addSeries(LineSeries, { color: '#3b82f6', lineWidth: 2, title: 'MA20' })
    ma20SeriesRef.current = ma20Series

    const ma60Series = chart.addSeries(LineSeries, { color: '#f59e0b', lineWidth: 2, title: 'MA60' })
    ma60SeriesRef.current = ma60Series

    const ma200Series = chart.addSeries(LineSeries, { color: '#a855f7', lineWidth: 2, title: 'MA200' })
    ma200SeriesRef.current = ma200Series

    const bbUpperSeries = chart.addSeries(LineSeries, { color: 'rgba(255, 255, 255, 0.3)', lineWidth: 1, title: 'BB Upper' })
    bbUpperSeriesRef.current = bbUpperSeries

    const bbLowerSeries = chart.addSeries(LineSeries, { color: 'rgba(255, 255, 255, 0.3)', lineWidth: 1, title: 'BB Lower' })
    bbLowerSeriesRef.current = bbLowerSeries

    // 響應式處理
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth })
      }
    }

    const handleVisibleRangeChange = () => {
      const range = chart.timeScale().getVisibleRange()
      const latestCandleTime = candleMetaRef.current[candleMetaRef.current.length - 1]?.time
      if (!range || !vpvrEnabledRef.current) {
        setVolumeProfile([])
        setVolumeProfileTotal(0)
        setPocPriceRange(null)
        setPocBand(null)
      } else {
        const fromSec = toUnixSeconds(range.from)
        const toSec = toUnixSeconds(range.to)
        if (fromSec !== null && toSec !== null) {
          buildVolumeProfileFromRange(fromSec, toSec)
        } else {
          const logicalRange = chart.timeScale().getVisibleLogicalRange()
          if (logicalRange) {
            buildVolumeProfileFromLogicalRange(logicalRange.from, logicalRange.to)
          }
        }
      }

      if (latestCandleTime && range) {
        const toSec = toUnixSeconds(range.to)
        if (toSec !== null) {
          // 使用者靠近最右側時才跟隨最新，若手動往左看歷史就不強制拉回
          followLatestRef.current = (latestCandleTime - toSec) <= 2 * 60 * 60
        }
      }
    }

    window.addEventListener('resize', handleResize)
    chart.timeScale().subscribeVisibleTimeRangeChange(handleVisibleRangeChange)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.timeScale().unsubscribeVisibleTimeRangeChange(handleVisibleRangeChange)
      if (chartRef.current) {
        chartRef.current.remove()
        chartRef.current = null
        candleSeriesRef.current = null
        volumeSeriesRef.current = null
        cvdSeriesRef.current = null
        ma20SeriesRef.current = null
        ma60SeriesRef.current = null
        ma200SeriesRef.current = null
        bbUpperSeriesRef.current = null
        bbLowerSeriesRef.current = null
        markersPluginRef.current = null
      }
    }
  }, [buildVolumeProfileFromLogicalRange, buildVolumeProfileFromRange, timeframe])

  // 更新資料
  useEffect(() => {
    if (!chartRef.current || !data || data.length === 0) return

    const candleData: CandlestickData[] = []
    const volumeData: HistogramData[] = []
    const ma20Data: LineData[] = []
    const ma60Data: LineData[] = []
    const ma200Data: LineData[] = []
    const bbUpperData: LineData[] = []
    const bbLowerData: LineData[] = []
    const candleMeta: Array<{ time: number; high: number; low: number; volume: number }> = []

    const seenTimes = new Set<number>()
    let lastTime: number | null = null;
    
    // 取得時間週期毫秒數 (用於檢測缺口)
    const getIntervalSeconds = () => {
      if (data.length < 2) return 60;
      return Math.floor((new Date(data[1].timestamp).getTime() - new Date(data[0].timestamp).getTime()) / 1000);
    };
    const intervalSeconds = getIntervalSeconds();

    for (let i = 0; i < data.length; i++) {
      const d = data[i]
      const time = Math.floor(new Date(d.timestamp).getTime() / 1000) as UTCTimestamp
      
      // 跳過無效時間或重複時間
      if (isNaN(time) || seenTimes.has(time)) continue
      seenTimes.add(time)

      // ✅ 檢測數據空洞 (Data Gap Detection)
      // 在 lightweight-charts 中，如果資料不連續，LineSeries 預設不會連起來，
      // 除非我們給了不連續的時間戳。
      // 但為了確保視覺上「斷開」而不是「斜線連接」，我們不需要額外插入 null，
      // 只需要確保 sorted 順序正確。
      // 截圖中的直線通常是因為後端回傳了重複的「最後價格」來填充缺口。
      
      lastTime = time;

      // 確保價格數值有效
      const open = Number(d.open)
      const high = Number(d.high)
      const low = Number(d.low)
      const close = Number(d.close)
      if (isNaN(open) || isNaN(high) || isNaN(low) || isNaN(close)) continue

      candleData.push({ time, open, high, low, close })
      candleMeta.push({ time: time as number, high, low, volume: Number(d.volume) || 0 })
      volumeData.push({
        time,
        value: Number(d.volume) || 0,
        color: close >= open ? 'rgba(34, 197, 94, 0.5)' : 'rgba(239, 68, 68, 0.5)',
      })

      if (d.sma_20 != null && !isNaN(Number(d.sma_20))) ma20Data.push({ time, value: Number(d.sma_20) })
      if (d.sma_60 != null && !isNaN(Number(d.sma_60))) ma60Data.push({ time, value: Number(d.sma_60) })
      if (d.sma_200 != null && !isNaN(Number(d.sma_200))) ma200Data.push({ time, value: Number(d.sma_200) })
      if (d.bollinger_upper != null && !isNaN(Number(d.bollinger_upper))) bbUpperData.push({ time, value: Number(d.bollinger_upper) })
      if (d.bollinger_lower != null && !isNaN(Number(d.bollinger_lower))) bbLowerData.push({ time, value: Number(d.bollinger_lower) })
    }

    // 確保資料按時間升序排列
    candleData.sort((a, b) => (a.time as number) - (b.time as number))
    volumeData.sort((a, b) => (a.time as number) - (b.time as number))
    ma20Data.sort((a, b) => (a.time as number) - (b.time as number))
    ma60Data.sort((a, b) => (a.time as number) - (b.time as number))
    ma200Data.sort((a, b) => (a.time as number) - (b.time as number))
    bbUpperData.sort((a, b) => (a.time as number) - (b.time as number))
    bbLowerData.sort((a, b) => (a.time as number) - (b.time as number))
    candleMeta.sort((a, b) => a.time - b.time)
    candleMetaRef.current = candleMeta

    // ✅ 使用 setData 更新資料（不會影響視圖範圍）
    if (candleSeriesRef.current) candleSeriesRef.current.setData(candleData)
    if (volumeSeriesRef.current) volumeSeriesRef.current.setData(volumeData)
    if (ma20SeriesRef.current) ma20SeriesRef.current.setData(ma20Data)
    if (ma60SeriesRef.current) ma60SeriesRef.current.setData(ma60Data)
    if (ma200SeriesRef.current) ma200SeriesRef.current.setData(ma200Data)
    if (bbUpperSeriesRef.current) bbUpperSeriesRef.current.setData(bbUpperData)
    if (bbLowerSeriesRef.current) bbLowerSeriesRef.current.setData(bbLowerData)

    // 由系統自動縮放主價格軸，避免固定範圍導致低點被截斷

    // ✅ 更新 CVD 數據 (對齊基準線)
    if (cvdSeriesRef.current && cvdData && cvdData.length > 0) {
      // 注意：API 可能回傳 DESC；先轉成 ASC 再做 baseline（用最早點歸零，右側顯示累積結果）
      const sorted = [...cvdData]
        .map(d => ({
          t: Math.floor(new Date(d.time).getTime() / 1000),
          v: Number(d.cvd)
        }))
        .filter(p => Number.isFinite(p.t) && Number.isFinite(p.v))
        .sort((a, b) => a.t - b.t);

      if (sorted.length > 0) {
        const baseline = sorted[0].v;
        const alignedCVD: LineData[] = sorted.map(p => ({
          time: p.t as UTCTimestamp,
          value: p.v - baseline
        }));
        cvdSeriesRef.current.setData(alignedCVD);
      }
    }

    // ✅ 僅在首次載入時設定視圖範圍
    if (isFirstLoadRef.current && chartRef.current && candleData.length > 0) {
      const barsByTimeframe: Record<string, number> = {
        '1m': 240,
        '5m': 220,
        '15m': 200,
        '1h': 180,
        '4h': 140,
        '1d': 120,
      }
      const targetBars = barsByTimeframe[timeframe] ?? 180
      const toIdx = candleData.length - 1
      const fromIdx = Math.max(0, toIdx - targetBars + 1)
      const from = candleData[fromIdx]?.time
      const to = candleData[toIdx]?.time
      if (from !== undefined && to !== undefined) {
        chartRef.current.timeScale().setVisibleRange({ from, to })
      } else {
        chartRef.current.timeScale().fitContent()
      }
      isFirstLoadRef.current = false
      followLatestRef.current = true
    } else if (chartRef.current && candleData.length > 1 && followLatestRef.current) {
      const timeScale = chartRef.current.timeScale()
      const range = timeScale.getVisibleRange()
      const latest = Number(candleData[candleData.length - 1].time)
      const prev = Number(candleData[candleData.length - 2].time)
      const step = Math.max(1, latest - prev)

      if (range) {
        const toSec = toUnixSeconds(range.to)
        const fromSec = toUnixSeconds(range.from)
        if (toSec !== null && fromSec !== null && latest > toSec) {
          const span = Math.max(step * 20, toSec - fromSec)
          const nextFrom = Math.max(0, latest - span)
          timeScale.setVisibleRange({
            from: nextFrom as UTCTimestamp,
            to: latest as UTCTimestamp,
          })
        }
      }
    }

    if (chartRef.current && visibleIndicators.vpvr) {
      const range = chartRef.current.timeScale().getVisibleRange()
      if (range) {
        const fromSec = toUnixSeconds(range.from)
        const toSec = toUnixSeconds(range.to)
        if (fromSec !== null && toSec !== null) {
          buildVolumeProfileFromRange(fromSec, toSec)
        } else {
          const logicalRange = chartRef.current.timeScale().getVisibleLogicalRange()
          if (logicalRange) {
            buildVolumeProfileFromLogicalRange(logicalRange.from, logicalRange.to)
          }
        }
      } else if (candleMeta.length > 0) {
        buildVolumeProfileFromRange(candleMeta[0].time, candleMeta[candleMeta.length - 1].time)
      }
    } else {
      setVolumeProfile([])
      setVolumeProfileTotal(0)
      setPocPriceRange(null)
      setPocBand(null)
    }

    // ✅ 處理爆倉標記 (Markers) - 資深交易員級優化：視覺強度區分
    if (markersPluginRef.current) {
      try {
        const liquidationMarkers: SeriesMarker<UTCTimestamp>[] = liquidations
          .filter(l => Number(l.value_usd) > 5000)
          .map(l => {
            const time = Math.floor(new Date(l.timestamp).getTime() / 1000) as UTCTimestamp;
            const isLongLiq = l.side === 'sell' || l.side === 'long_liquidated'; 
            const value = Number(l.value_usd);
            
            // 根據爆倉金額決定大小 (Size 1-4)
            let size: 1 | 2 | 3 | 4 = 1;
            if (value > 1000000) size = 4;      // > $1M: 極大標記
            else if (value > 200000) size = 3;  // > $200k: 大標記
            else if (value > 50000) size = 2;   // > $50k: 中標記
            
            return {
              time,
              position: isLongLiq ? 'belowBar' : 'aboveBar',
              color: isLongLiq ? '#ef4444' : '#22c55e',
              shape: isLongLiq ? 'arrowDown' : 'arrowUp',
              text: value > 100000 ? `Liq $${(value / 1000).toFixed(0)}k` : '', // 僅大額顯示文字
              size: size
            };
          });

        const fractalMarkers: SeriesMarker<UTCTimestamp>[] = []
        if (visibleIndicators.fractal) {
          for (const d of data) {
            const time = Math.floor(new Date(d.timestamp).getTime() / 1000) as UTCTimestamp
            if (d.fractal_up) {
              fractalMarkers.push({
                time,
                position: 'aboveBar',
                color: '#f97316',
                shape: 'arrowDown',
                text: '',
                size: 1,
              })
            } else if (d.fractal_down) {
              fractalMarkers.push({
                time,
                position: 'belowBar',
                color: '#22c55e',
                shape: 'arrowUp',
                text: '',
                size: 1,
              })
            }
          }
        }

        const markers: SeriesMarker<UTCTimestamp>[] = [...liquidationMarkers, ...fractalMarkers]

        // 確保標記按時間排序且不重複 (Lightweight charts 限制)
        // 若同一秒有多筆爆倉，取金額最大的一筆
        const markerMap = new Map<number, SeriesMarker<UTCTimestamp>>();
        markers.forEach(m => {
          const existing = markerMap.get(m.time as number);
          if (!existing || (m.size || 0) > (existing.size || 0)) {
            markerMap.set(m.time as number, m);
          }
        });

        const uniqueMarkers = Array.from(markerMap.values())
          .sort((a, b) => (a.time as number) - (b.time as number));
          
        markersPluginRef.current.setMarkers(uniqueMarkers);
      } catch (err) {
        console.error('Failed to set markers:', err);
      }
    }
  }, [buildVolumeProfileFromLogicalRange, buildVolumeProfileFromRange, data, liquidations, cvdData, timeframe, visibleIndicators.fractal, visibleIndicators.vpvr])

  useEffect(() => {
    if (!visibleIndicators.vpvr || !pocPriceRange || !candleSeriesRef.current) {
      setPocBand(null)
      return
    }

    const updateBandCoordinates = () => {
      const series = candleSeriesRef.current
      if (!series) return

      const upperY = series.priceToCoordinate(pocPriceRange.upper)
      const lowerY = series.priceToCoordinate(pocPriceRange.lower)
      const centerY = series.priceToCoordinate(pocPriceRange.center)
      if (upperY == null || lowerY == null || centerY == null) {
        setPocBand(null)
        return
      }

      const topPx = Math.min(upperY, lowerY)
      const heightPx = Math.max(1, Math.abs(lowerY - upperY))
      setPocBand({ topPx, heightPx, centerPx: centerY })
    }

    updateBandCoordinates()
    const raf = requestAnimationFrame(updateBandCoordinates)
    return () => cancelAnimationFrame(raf)
  }, [visibleIndicators.vpvr, pocPriceRange, data, timeframe])

  // 更新指標可見性
  useEffect(() => {
    if (ma20SeriesRef.current) ma20SeriesRef.current.applyOptions({ visible: visibleIndicators.ma20 })
    if (ma60SeriesRef.current) ma60SeriesRef.current.applyOptions({ visible: visibleIndicators.ma60 })
    if (ma200SeriesRef.current) ma200SeriesRef.current.applyOptions({ visible: visibleIndicators.ma200 })
    if (bbUpperSeriesRef.current) bbUpperSeriesRef.current.applyOptions({ visible: visibleIndicators.bb })
    if (bbLowerSeriesRef.current) bbLowerSeriesRef.current.applyOptions({ visible: visibleIndicators.bb })
  }, [visibleIndicators])

  return (
    <div className="relative">
      <div ref={chartContainerRef} className="w-full" />

      {visibleIndicators.vpvr && pocBand && (
        <>
          <div
            className="absolute left-0 right-0 z-10 bg-gray-300/20 border-y border-gray-300/40 pointer-events-none"
            style={{
              top: `${pocBand.topPx}px`,
              height: `${pocBand.heightPx}px`,
            }}
            title="VPVR POC Zone"
          />
          <div
            className="absolute left-0 right-0 z-20 border-t border-gray-200/70 pointer-events-none"
            style={{ top: `${pocBand.centerPx}px` }}
            title="VPVR POC Center"
          />
        </>
      )}
      
      {/* 圖例 */}
      <div className="absolute z-20 top-2 left-2 bg-gray-900/80 backdrop-blur-sm px-3 py-2 rounded-md text-xs space-y-1 border border-gray-700">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-green-500 rounded-sm"></div>
          <span className="text-gray-300">漲 (Close ≥ Open)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-red-500 rounded-sm"></div>
          <span className="text-gray-300">跌 (Close &lt; Open)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-8 h-0.5 bg-blue-500"></div>
          <span className="text-gray-300">MA 20</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-8 h-0.5 bg-amber-500"></div>
          <span className="text-gray-300">MA 60</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-8 h-0.5 bg-purple-500"></div>
          <span className="text-gray-300">MA 200</span>
        </div>
        {visibleIndicators.fractal && (
          <div className="flex items-center gap-2">
            <div className="text-orange-400 text-[10px]">▼</div>
            <span className="text-gray-300">Williams Fractal</span>
          </div>
        )}
      </div>

      {visibleIndicators.vpvr && (
        <div className="absolute z-20 top-2 right-2 bottom-8 w-48 bg-gray-900/50 backdrop-blur-[1px] rounded border border-gray-700/70 p-2 pointer-events-none">
          <div className="flex items-center justify-between mb-2">
            <div className="text-[10px] font-bold text-gray-300">VPVR</div>
            <div className="text-[9px] text-gray-500">
              {volumeProfileTotal.toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </div>
          </div>
          <div className="relative h-[calc(100%-20px)] flex flex-col justify-stretch gap-[1px]">
            {volumeProfile.length === 0 && (
              <div className="text-[10px] text-gray-500 h-full flex items-center justify-center">No visible bars</div>
            )}
            {volumeProfile.map((row) => {
              const widthPct = Math.max(2, Math.round(row.ratio * 100))
              const isPoc = row.ratio >= 0.999
              return (
                <div key={`${row.lower}-${row.upper}`} className="relative flex-1 min-h-[2px]">
                  <div className="absolute inset-y-0 right-0 w-full bg-gray-800/30 rounded-sm" />
                  <div
                    className={`absolute inset-y-0 right-0 rounded-sm ${isPoc ? 'bg-orange-300/95' : 'bg-orange-400/75'}`}
                    style={{ width: `${widthPct}%` }}
                  />
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* 操作提示 */}
      <div className="mt-2 text-xs text-gray-500 text-center">
        拖動圖表可平移 | 滾輪可縮放 | 點擊可查看十字線
      </div>
    </div>
  )
}
