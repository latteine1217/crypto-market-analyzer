'use client'

import { useState, useMemo, memo, useRef, useCallback, useEffect, Suspense } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useRouter, useSearchParams, usePathname } from 'next/navigation'
import type { IChartApi } from 'lightweight-charts'
import { 
  fetchOHLCV, 
  fetchMarkets, 
  fetchFundingRate, 
  fetchOpenInterest,
  fetchLatestOrderbook,
  fetchCVD,
  fetchLiquidations
} from '@/lib/api-client'
import { calculateAllIndicators } from '@/lib/indicators'
import { LightweightCandlestickChart } from '@/components/charts/LightweightCandlestickChart'
import { MACDChart } from '@/components/charts/MACDChart'
import { FundingRateChart } from '@/components/charts/FundingRateChart'
import { OpenInterestChart } from '@/components/charts/OpenInterestChart'
import { DepthChart } from '@/components/charts/DepthChart'
import { IndicatorStats } from '@/components/IndicatorStats'
import { AlertsManager } from '@/components/AlertsManager'
import { SignalTimeline } from '@/components/SignalTimeline'

// Memoize components to prevent re-renders when visibility toggles
const MemoizedMACDChart = memo(MACDChart)
const MemoizedFundingRateChart = memo(FundingRateChart)
const MemoizedOpenInterestChart = memo(OpenInterestChart)
const MemoizedDepthChart = memo(DepthChart)
const MemoizedIndicatorStats = memo(IndicatorStats)
const MemoizedLightweightCandlestickChart = memo(LightweightCandlestickChart)

function TechnicalContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const pathname = usePathname()

  // 僅允許 Bybit，防止舊 URL 導致空白
  const validExchanges = ['bybit']
  const queryExchange = searchParams.get('exchange')
  const initialExchange = (queryExchange && validExchanges.includes(queryExchange)) ? queryExchange : 'bybit'

  const initialSymbol = searchParams.get('symbol') || 'BTCUSDT'
  const initialTimeframe = searchParams.get('timeframe') || '1h'

  const [exchange, setExchange] = useState(initialExchange)
  const [symbol, setSymbol] = useState(initialSymbol)
  const [timeframe, setTimeframe] = useState(initialTimeframe)

  // 當狀態改變時更新 URL
  useEffect(() => {
    const params = new URLSearchParams(searchParams.toString())
    params.set('exchange', exchange)
    params.set('symbol', symbol)
    params.set('timeframe', timeframe)
    
    // 使用 replace 避免在瀏覽紀錄中堆疊過多切換
    router.replace(`${pathname}?${params.toString()}`, { scroll: false })
  }, [exchange, symbol, timeframe, pathname, router, searchParams])

  // 指標可見性狀態
  const [visibleIndicators, setVisibleIndicators] = useState({
    ma20: true,
    ma60: true,
    ma200: true,
    bb: false,
    macd: true,
    oi: true,
    depth: false,
  })

  const { data: markets } = useQuery({
    queryKey: ['markets'],
    queryFn: fetchMarkets,
  })

  const { data: ohlcv, isLoading } = useQuery({
    queryKey: ['ohlcv', exchange, symbol, timeframe],
    queryFn: () => fetchOHLCV(exchange, symbol, { limit: 500, timeframe }),
    refetchInterval: 15000,
  })

  const { data: cvdData } = useQuery({
    queryKey: ['cvd', exchange, symbol, timeframe],
    queryFn: () => fetchCVD(exchange, symbol, timeframe, 500),
    refetchInterval: 10000,
  })

  const { data: liquidations } = useQuery({
    queryKey: ['liquidations', exchange, symbol],
    queryFn: () => fetchLiquidations(exchange, symbol, 100),
    refetchInterval: 5000,
  })

  const { data: orderbook } = useQuery({
    queryKey: ['orderbook', exchange, symbol],
    queryFn: () => fetchLatestOrderbook(exchange, symbol),
    refetchInterval: 5000,
    enabled: visibleIndicators.depth,
  })

  // 圖表引用管理
  const chartsRef = useRef<Map<string, IChartApi>>(new Map())
  const syncHandlersRef = useRef<Map<string, (range: any) => void>>(new Map())

  const onChartCreate = useCallback((id: string, chart: IChartApi) => {
    console.log(`[Chart Debug] Registering chart: ${id}`);
    chartsRef.current.set(id, chart)
  }, [])

  // 同步邏輯 - 使用防抖機制避免循環觸發
  const isSyncSetupRef = useRef(false)
  const isSyncingRef = useRef(false) // 防止循環同步的標記
  
  useEffect(() => {
    const charts = chartsRef.current
    
    // 如果已經設定過同步且圖表數量沒變化，則不重新綁定
    if (isSyncSetupRef.current && charts.size > 0) return
    
    // 清理舊的監聽器
    charts.forEach((chart, id) => {
      const oldHandler = syncHandlersRef.current.get(id)
      if (oldHandler) {
        chart.timeScale().unsubscribeVisibleTimeRangeChange(oldHandler)
      }
    })
    syncHandlersRef.current.clear()

    // 監聽任何一個圖表的時間範圍變化，並同步到其他圖表
    const createSyncHandler = (sourceId: string) => (range: any) => {
      if (!range || isSyncingRef.current) return
      
      // 設置同步標記，防止循環觸發
      isSyncingRef.current = true
      
      const currentCharts = chartsRef.current
      currentCharts.forEach((chart, id) => {
        if (id !== sourceId) {
          try {
            // 💡 核心修正：僅同步時間範圍，且明確告知不要同步座標軸
            chart.timeScale().setVisibleRange(range)
          } catch (e) {
            // 忽略範圍設定錯誤
          }
        }
      })
      
      // 使用 setTimeout 確保所有同步操作完成後再重置標記
      setTimeout(() => {
        isSyncingRef.current = false
      }, 0)
    }

    // 為所有圖表註冊監聽器
    charts.forEach((chart, id) => {
      const handler = createSyncHandler(id)
      syncHandlersRef.current.set(id, handler)
      chart.timeScale().subscribeVisibleTimeRangeChange(handler)
    })
    
    isSyncSetupRef.current = true

    return () => {
      const currentCharts = chartsRef.current
      currentCharts.forEach((chart, id) => {
        const handler = syncHandlersRef.current.get(id)
        if (handler) {
          chart.timeScale().unsubscribeVisibleTimeRangeChange(handler)
        }
      })
    }
  }, []) // ✅ 空依賴陣列 - 僅在組件掛載時執行一次

  const { data: fundingRate } = useQuery({
    queryKey: ['funding-rate', exchange, symbol],
    queryFn: () => fetchFundingRate(exchange, symbol, 100),
    refetchInterval: 30000,
    enabled: ['bybit', 'binance', 'okx'].includes(exchange.toLowerCase()),
  })

  const { data: openInterest } = useQuery({
    queryKey: ['open-interest', exchange, symbol],
    queryFn: () => fetchOpenInterest(exchange, symbol, 500),
    refetchInterval: 30000,
    enabled: ['bybit', 'binance', 'okx'].includes(exchange.toLowerCase()),
  })

  // 合併與計算指標
  const dataWithIndicators = useMemo(() => {
    if (!ohlcv || ohlcv.length === 0) return null
    
    // 1. 基本指標計算
    const indicators = calculateAllIndicators(ohlcv)
    
    // 2. 對齊 OI 與 Funding Rate (如果有)
    return indicators.map(d => {
      const ts = new Date(d.timestamp).getTime()
      
      // 尋找最近的 OI (OI 頻率可能較低)
      let oi_val = undefined
      let oi_usd = undefined
      if (openInterest && openInterest.length > 0) {
        // 尋找最近點邏輯（放寬到 1 小時，以對齊每小時一次的資料）
        const closestOi = openInterest.find(oi => 
          Math.abs(new Date(oi.timestamp).getTime() - ts) < 3600000 // 1 小時內
        )
        if (closestOi) {
          oi_val = closestOi.open_interest
          oi_usd = closestOi.open_interest_usd || undefined
        }
      }

      // 尋找最近的 Funding Rate
      let fr_val = undefined
      if (fundingRate && fundingRate.length > 0) {
        // 尋找最近點邏輯（放寬到 4 小時，對齊 8h 一次的資金費率）
        const closestFr = fundingRate.find(fr => 
          Math.abs(new Date(fr.timestamp).getTime() - ts) < 14400000 // 4 小時內
        )
        if (closestFr) {
          fr_val = closestFr.funding_rate
        }
      }

      return {
        ...d,
        open_interest: oi_val,
        open_interest_usd: oi_usd,
        funding_rate: fr_val
      }
    })
  }, [ohlcv, openInterest, fundingRate])

  const filteredMarkets = markets?.filter(m => m.exchange === exchange)

  const toggleIndicator = (key: keyof typeof visibleIndicators) => {
    setVisibleIndicators(prev => ({ ...prev, [key]: !prev[key] }))
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold mb-2">Technical Analysis</h1>
          <p className="text-gray-400">Candlestick charts with technical indicators & derivatives data</p>
        </div>

        <div className="flex flex-wrap gap-4">
          <select
            value={exchange}
            onChange={(e) => setExchange(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded px-4 py-2"
          >
            <option value="bybit">Bybit</option>
          </select>

          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded px-4 py-2 min-w-[150px]"
          >
            {filteredMarkets?.map(m => (
              <option key={m.id} value={m.symbol}>
                {m.symbol}
              </option>
            ))}
          </select>

          <div className="flex bg-gray-800 rounded p-1 border border-gray-700">
            {['1m', '5m', '15m', '1h', '4h', '1d'].map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-3 py-1 text-sm rounded transition-colors ${
                  timeframe === tf
                    ? 'bg-primary text-white font-medium'
                    : 'text-gray-400 hover:text-white hover:bg-gray-700'
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>
      </div>

      {isLoading && (
        <div className="space-y-6 animate-pulse">
          <div className="h-64 bg-gray-800/50 rounded-xl border border-gray-700 flex items-center justify-center">
            <div className="flex flex-col items-center">
              <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-4"></div>
              <p className="text-gray-400">Fetching market data...</p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="h-48 bg-gray-800/50 rounded-xl border border-gray-700"></div>
            <div className="h-48 bg-gray-800/50 rounded-xl border border-gray-700"></div>
          </div>
        </div>
      )}

      {dataWithIndicators && (
        <>
          {/* 指標控制面板 */}
          <div className="flex flex-wrap gap-2 items-center bg-gray-900/50 p-2 rounded-lg border border-gray-800">
            <span className="text-sm text-gray-400 mr-2 px-2">Indicators:</span>
            
            <label className="flex items-center space-x-2 px-3 py-1 bg-gray-800 rounded cursor-pointer hover:bg-gray-700 transition-colors">
              <input 
                type="checkbox" 
                checked={visibleIndicators.ma20} 
                onChange={() => toggleIndicator('ma20')}
                className="rounded border-gray-600 text-blue-500 focus:ring-blue-500 bg-gray-700"
              />
              <span className="text-sm text-blue-400">MA 20</span>
            </label>

            <label className="flex items-center space-x-2 px-3 py-1 bg-gray-800 rounded cursor-pointer hover:bg-gray-700 transition-colors">
              <input 
                type="checkbox" 
                checked={visibleIndicators.ma60} 
                onChange={() => toggleIndicator('ma60')}
                className="rounded border-gray-600 text-amber-500 focus:ring-amber-500 bg-gray-700"
              />
              <span className="text-sm text-amber-500">MA 60</span>
            </label>

            <label className="flex items-center space-x-2 px-3 py-1 bg-gray-800 rounded cursor-pointer hover:bg-gray-700 transition-colors">
              <input 
                type="checkbox" 
                checked={visibleIndicators.ma200} 
                onChange={() => toggleIndicator('ma200')}
                className="rounded border-gray-600 text-purple-500 focus:ring-purple-500 bg-gray-700"
              />
              <span className="text-sm text-purple-500">MA 200</span>
            </label>

            <label className="flex items-center space-x-2 px-3 py-1 bg-gray-800 rounded cursor-pointer hover:bg-gray-700 transition-colors">
              <input 
                type="checkbox" 
                checked={visibleIndicators.bb} 
                onChange={() => toggleIndicator('bb')}
                className="rounded border-gray-600 text-cyan-500 focus:ring-cyan-500 bg-gray-700"
              />
              <span className="text-sm text-cyan-400">Bollinger Bands</span>
            </label>
            
            <label className="flex items-center space-x-2 px-3 py-1 bg-gray-800 rounded cursor-pointer hover:bg-gray-700 transition-colors">
              <input 
                type="checkbox" 
                checked={visibleIndicators.macd} 
                onChange={() => toggleIndicator('macd')}
                className="rounded border-gray-600 text-gray-400 focus:ring-gray-500 bg-gray-700"
              />
              <span className="text-sm text-gray-300">MACD</span>
            </label>

            <label className="flex items-center space-x-2 px-3 py-1 bg-gray-800 rounded cursor-pointer hover:bg-gray-700 transition-colors">
              <input 
                type="checkbox" 
                checked={visibleIndicators.oi} 
                onChange={() => toggleIndicator('oi')}
                className="rounded border-gray-600 text-purple-500 focus:ring-purple-500 bg-gray-700"
              />
              <span className="text-sm text-purple-400">Open Interest</span>
            </label>
            <label className="flex items-center space-x-2 px-3 py-1 bg-gray-800 rounded cursor-pointer hover:bg-gray-700 transition-colors">
              <input 
                type="checkbox" 
                checked={visibleIndicators.depth} 
                onChange={() => toggleIndicator('depth')}
                className="rounded border-gray-600 text-teal-500 focus:ring-teal-500 bg-gray-700"
              />
              <span className="text-sm text-teal-400">Depth</span>
            </label>
          </div>

          {/* K 線圖與移動平均 */}
          <div className="card">
            <h2 className="card-header">Candlestick Chart</h2>
            <MemoizedLightweightCandlestickChart 
              data={dataWithIndicators} 
              cvdData={cvdData?.map(d => ({ time: d.time, cvd: d.cvd }))}
              liquidations={liquidations}
              visibleIndicators={visibleIndicators}
              onChartCreate={(chart) => onChartCreate('main', chart)}
              key={`${exchange}-${symbol}-${timeframe}`}
            />
          </div>

          {/* MACD 指標 (可選顯示) */}
          {visibleIndicators.macd && (
            <div className="card">
              <h2 className="card-header">MACD Indicator</h2>
              <MemoizedMACDChart 
                data={dataWithIndicators} 
                onChartCreate={(chart) => onChartCreate('macd', chart)}
                key={`macd-${exchange}-${symbol}-${timeframe}`}
              />
            </div>
          )}

          {/* 資金費率 */}
          {fundingRate && fundingRate.length > 0 && (
            <div className="card">
              <h2 className="card-header">Funding Rate (Perpetual)</h2>
              <MemoizedFundingRateChart 
                data={fundingRate} 
                onChartCreate={(chart) => onChartCreate('funding', chart)}
                key={`funding-${exchange}-${symbol}`}
              />
            </div>
          )}

          {/* 持倉量 (同步版) */}
          {visibleIndicators.oi && openInterest && openInterest.length > 0 && (
            <div className="card">
              <h2 className="card-header">Open Interest</h2>
              <MemoizedOpenInterestChart 
                data={openInterest} 
                onChartCreate={(chart) => onChartCreate('oi', chart)}
                key={`oi-${exchange}-${symbol}`}
              />
            </div>
          )}

          {/* 深度圖 */}
          {visibleIndicators.depth && orderbook && (
            <div className="card">
              <h2 className="card-header">Order Book Depth</h2>
              <MemoizedDepthChart orderbook={orderbook} />
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            <div className="lg:col-span-1 space-y-6">
              <AlertsManager 
                currentSymbol={symbol} 
                currentPrice={dataWithIndicators[dataWithIndicators.length - 1]?.close} 
              />
              <SignalTimeline symbol={symbol} />
            </div>

            <div className="lg:col-span-3 card">
              <h2 className="card-header">Technical Indicators</h2>
              <MemoizedIndicatorStats data={dataWithIndicators} />
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default function TechnicalPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    }>
      <TechnicalContent />
    </Suspense>
  )
}