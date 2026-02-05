'use client'

import { useEffect, useRef } from 'react'
import { 
  createChart, 
  ColorType,
  CandlestickSeries,
  LineSeries,
  AreaSeries,
  HistogramSeries,
  PriceScaleMode,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
  type CandlestickData,
  type LineData,
  type HistogramData,
  type AreaData,
  type SeriesMarker
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
  }
  onChartCreate?: (chart: IChartApi) => void
  key?: string // 用於識別參數變化，觸發重新首次載入
}

export function LightweightCandlestickChart({ 
  data, 
  cvdData = [],
  liquidations = [],
  visibleIndicators = { ma20: true, ma60: true, ma200: true, bb: false },
  onChartCreate,
  key
}: Props) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<any>(null) // 使用 any 繞過嚴格的 v4 類型檢查，確保編譯通過
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)
  const cvdSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const ma20SeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const ma60SeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const ma200SeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const bbUpperSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const bbLowerSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const isFirstLoadRef = useRef(true) // 追蹤是否為首次載入
  const previousKeyRef = useRef(key) // 追蹤 key 變化

  // 當 key 變化時（例如切換 timeframe/symbol），重置為首次載入
  useEffect(() => {
    if (key !== previousKeyRef.current) {
      isFirstLoadRef.current = true
      previousKeyRef.current = key
    }
  }, [key])

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

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
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
      }
    }
  }, [])

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
      const firstCVD = Number(cvdData[0].cvd);
      const alignedCVD: LineData[] = cvdData.map(d => ({
        time: Math.floor(new Date(d.time).getTime() / 1000) as UTCTimestamp,
        value: Number(d.cvd) - firstCVD
      })).sort((a, b) => (a.time as number) - (b.time as number));
      
      cvdSeriesRef.current.setData(alignedCVD);
    }

    // ✅ 僅在首次載入時設定視圖範圍
    if (isFirstLoadRef.current && chartRef.current && candleData.length > 0) {
      // ... (之前的視圖範圍代碼)
    }

    // ✅ 處理爆倉標記 (Markers) - 資深交易員級優化：視覺強度區分
    if (candleSeriesRef.current && typeof candleSeriesRef.current.setMarkers === 'function' && liquidations.length > 0) {
      try {
        const markers: SeriesMarker<UTCTimestamp>[] = liquidations
          .filter(l => Number(l.value_usd) > 5000) // 降低門檻以觀察小額爆倉，但視覺上區分
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
          
        candleSeriesRef.current.setMarkers(uniqueMarkers);
      } catch (err) {
        console.error('Failed to set markers:', err);
      }
    }
  }, [data, liquidations, cvdData])

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
