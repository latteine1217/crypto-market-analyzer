'use client'

import { useEffect, useRef } from 'react'
import { 
  createChart, 
  ColorType,
  CandlestickSeries,
  LineSeries,
  AreaSeries,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
  type CandlestickData,
  type LineData,
  type HistogramData,
  type AreaData
} from 'lightweight-charts'
import type { OHLCVWithIndicators } from '@/types/market'

interface Props {
  data: OHLCVWithIndicators[]
  visibleIndicators?: {
    ma20: boolean
    ma60: boolean
    ma200: boolean
    bb: boolean
  }
}

export function LightweightCandlestickChart({ 
  data, 
  visibleIndicators = { ma20: true, ma60: true, ma200: true, bb: false } 
}: Props) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const ma20SeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const ma60SeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const ma200SeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const bbUpperSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const bbLowerSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const bbFillUpperSeriesRef = useRef<ISeriesApi<'Area'> | null>(null)
  const bbFillLowerSeriesRef = useRef<ISeriesApi<'Area'> | null>(null)

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
      },
      timeScale: {
        borderColor: '#374151',
        timeVisible: true,
        secondsVisible: false,
      },
      crosshair: {
        mode: 1,
      },
    })

    chartRef.current = chart

    // 創建 Bollinger Bands 填充區域 (Cloud)
    // 第一層：Upper 填充（淺白色）
    const bbFillUpperSeries = chart.addSeries(AreaSeries, {
      topColor: 'rgba(255, 255, 255, 0.05)',
      bottomColor: 'rgba(255, 255, 255, 0.05)',
      lineVisible: false,
      priceLineVisible: false,
      lastValueVisible: false,
    })
    bbFillUpperSeriesRef.current = bbFillUpperSeries

    // 第二層：Lower 遮罩（背景色，用來挖空 Lower 以下的區域）
    const bbFillLowerSeries = chart.addSeries(AreaSeries, {
      topColor: '#111827',
      bottomColor: '#111827',
      lineVisible: false,
      priceLineVisible: false,
      lastValueVisible: false,
    })
    bbFillLowerSeriesRef.current = bbFillLowerSeries

    // 創建 K 線序列 (使用 v5 API)
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderUpColor: '#22c55e',
      borderDownColor: '#ef4444',
      wickUpColor: '#22c55e',
      wickDownColor: '#ef4444',
    })
    candleSeriesRef.current = candleSeries

    // 創建 MA20 線
    const ma20Series = chart.addSeries(LineSeries, {
      color: '#3b82f6', // Blue
      lineWidth: 2,
      title: 'MA20',
    })
    ma20SeriesRef.current = ma20Series

    // 創建 MA60 線
    const ma60Series = chart.addSeries(LineSeries, {
      color: '#f59e0b', // Amber
      lineWidth: 2,
      title: 'MA60',
    })
    ma60SeriesRef.current = ma60Series

    // 創建 MA200 線
    const ma200Series = chart.addSeries(LineSeries, {
      color: '#a855f7', // Purple
      lineWidth: 2,
      title: 'MA200',
    })
    ma200SeriesRef.current = ma200Series

    // 創建 Bollinger Bands (Upper)
    const bbUpperSeries = chart.addSeries(LineSeries, {
      color: 'rgba(255, 255, 255, 0.3)', // Faint White
      lineWidth: 1,
      title: 'BB Upper',
      lineStyle: 0, // Solid
    })
    bbUpperSeriesRef.current = bbUpperSeries

    // 創建 Bollinger Bands (Lower)
    const bbLowerSeries = chart.addSeries(LineSeries, {
      color: 'rgba(255, 255, 255, 0.3)', // Faint White
      lineWidth: 1,
      title: 'BB Lower',
      lineStyle: 0, // Solid
    })
    bbLowerSeriesRef.current = bbLowerSeries

    // 響應式處理
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
        })
      }
    }

    window.addEventListener('resize', handleResize)

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize)
      if (chartRef.current) {
        chartRef.current.remove()
        chartRef.current = null
      }
      candleSeriesRef.current = null
      ma20SeriesRef.current = null
      ma60SeriesRef.current = null
      ma200SeriesRef.current = null
      bbUpperSeriesRef.current = null
      bbLowerSeriesRef.current = null
      bbFillUpperSeriesRef.current = null
      bbFillLowerSeriesRef.current = null
    }
  }, [])

  // 更新資料
  useEffect(() => {
    const candleSeries = candleSeriesRef.current;
    const ma20Series = ma20SeriesRef.current;
    const ma60Series = ma60SeriesRef.current;
    const ma200Series = ma200SeriesRef.current;
    const bbUpperSeries = bbUpperSeriesRef.current;
    const bbLowerSeries = bbLowerSeriesRef.current;

    if (!candleSeries || !ma20Series || !ma60Series || !ma200Series || !bbUpperSeries || !bbLowerSeries) return
    if (!data || data.length === 0) return

    const candleData: CandlestickData[] = []
    const ma20Data: LineData[] = []
    const ma60Data: LineData[] = []
    const ma200Data: LineData[] = []
    const bbUpperData: LineData[] = []
    const bbLowerData: LineData[] = []

    // 單次循環處理所有資料，大幅提升效能
    for (let i = 0; i < data.length; i++) {
      const d = data[i]
      const time = Math.floor(new Date(d.timestamp).getTime() / 1000) as UTCTimestamp

      candleData.push({
        time,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      })

      if (d.sma_20 != null) ma20Data.push({ time, value: d.sma_20 })
      if (d.sma_60 != null) ma60Data.push({ time, value: d.sma_60 })
      if (d.sma_200 != null) ma200Data.push({ time, value: d.sma_200 })
      if (d.bollinger_upper != null) bbUpperData.push({ time, value: d.bollinger_upper })
      if (d.bollinger_lower != null) bbLowerData.push({ time, value: d.bollinger_lower })
    }

    // 設定資料
    candleSeries.setData(candleData)
    ma20Series.setData(ma20Data)
    ma60Series.setData(ma60Data)
    ma200Series.setData(ma200Data)
    bbUpperSeries.setData(bbUpperData)
    bbLowerSeries.setData(bbLowerData)

    // 自動調整可見範圍 (只在第一次或資料長度大幅改變時執行，避免擾亂用戶縮放)
    if (chartRef.current && data.length > 0) {
      // 可以考慮只在初始化時 fitContent
      // chartRef.current.timeScale().fitContent()
    }
  }, [data])

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
      
      {/* 圖例 */}
      <div className="absolute top-2 left-2 bg-gray-900/80 backdrop-blur-sm px-3 py-2 rounded-md text-xs space-y-1 border border-gray-700">
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
      </div>

      {/* 操作提示 */}
      <div className="mt-2 text-xs text-gray-500 text-center">
        拖動圖表可平移 | 滾輪可縮放 | 點擊可查看十字線
      </div>
    </div>
  )
}
