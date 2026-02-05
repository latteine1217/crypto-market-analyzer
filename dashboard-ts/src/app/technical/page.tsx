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
    queryFn: () => fetchOHLCV(exchange, symbol, { limit: 2000, timeframe }),
    refetchInterval: 2000, // 提升至 2秒，讓 K 線收盤更及時
  })

  const { data: cvdData } = useQuery({
    queryKey: ['cvd', exchange, symbol, timeframe],
    queryFn: () => fetchCVD(exchange, symbol, timeframe, 500),
    refetchInterval: 5000, // 提升至 5秒
  })

  const { data: liquidations } = useQuery({
    queryKey: ['liquidations', exchange, symbol],
    queryFn: () => fetchLiquidations(exchange, symbol, 100),
    refetchInterval: 5000,
  })

  const { data: orderbook } = useQuery({
    queryKey: ['orderbook', exchange, symbol],
    queryFn: () => fetchLatestOrderbook(exchange, symbol),
    refetchInterval: 1000, // ⚡️ 1秒極速刷新 (配合 Redis 實時數據)
    enabled: visibleIndicators.depth,
  })

  const { data: fundingRate } = useQuery({
    queryKey: ['funding-rate', exchange, symbol],
    queryFn: () => fetchFundingRate(exchange, symbol, 100),
    refetchInterval: 10000,
    enabled: ['bybit', 'binance', 'okx'].includes((exchange || '').toLowerCase()),
  })

  const { data: openInterest } = useQuery({
    queryKey: ['open-interest', exchange, symbol],
    queryFn: () => fetchOpenInterest(exchange, symbol, 500),
    refetchInterval: 10000,
    enabled: ['bybit', 'binance', 'okx'].includes((exchange || '').toLowerCase()),
  })

  // ✅ 合併與計算指標 (必須在 useEffect 之前定義)
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

  // 圖表引用管理
  const chartsRef = useRef<Map<string, IChartApi>>(new Map())
  const syncHandlersRef = useRef<Map<string, (range: any) => void>>(new Map())
  const isSyncingRef = useRef(false)

  const onChartCreate = useCallback((id: string, chart: IChartApi) => {
    console.log(`[Chart Sync] Registering chart: ${id}`);
    chartsRef.current.set(id, chart)
    
    // 如果已有同步範圍，新圖表建立時立即對齊
    if (chartsRef.current.size > 1) {
      const firstChart = Array.from(chartsRef.current.values())[0]
      const range = firstChart.timeScale().getVisibleRange()
      if (range) {
        try { chart.timeScale().setVisibleRange(range) } catch(e) {}
      }
    }
  }, [])

  // 同步邏輯 - 強化版 (解決不同步問題)
  useEffect(() => {
    const charts = chartsRef.current
    if (charts.size === 0) return

    // 1. 先徹底清理所有舊的監聽器
    charts.forEach((chart, id) => {
      const oldHandler = syncHandlersRef.current.get(id)
      if (oldHandler) {
        try { chart.timeScale().unsubscribeVisibleTimeRangeChange(oldHandler) } catch (e) {}
      }
    })
    syncHandlersRef.current.clear()

    // 2. 定義統一的同步處理器
    const handleSync = (sourceId: string, range: any) => {
      if (!range || isSyncingRef.current) return
      isSyncingRef.current = true
      
      charts.forEach((chart, id) => {
        if (id !== sourceId) {
          try {
            chart.timeScale().setVisibleRange(range)
          } catch (e) {
            // 如果圖表已銷毀但還在 Map 裡，這裡會出錯，我們忽略它
          }
        }
      })
      
      // 使用小延遲防止循環觸發
      setTimeout(() => { isSyncingRef.current = false }, 50)
    }

    // 3. 為當前所有存在的圖表重新綁定
    charts.forEach((chart, id) => {
      const handler = (range: any) => handleSync(id, range)
      syncHandlersRef.current.set(id, handler)
      chart.timeScale().subscribeVisibleTimeRangeChange(handler)
    })

    return () => {
      charts.forEach((chart, id) => {
        const handler = syncHandlersRef.current.get(id)
        if (handler) {
          try { chart.timeScale().unsubscribeVisibleTimeRangeChange(handler) } catch (e) {}
        }
      })
    }
  }, [visibleIndicators, dataWithIndicators, openInterest, fundingRate]) // 關鍵：數據變化時重新綁定同步

  const filteredMarkets = markets?.filter(m => m.exchange === exchange)

  const toggleIndicator = (key: keyof typeof visibleIndicators) => {
    setVisibleIndicators(prev => ({ ...prev, [key]: !prev[key] }))
  }

  return (
    <div className="max-w-[1800px] mx-auto space-y-4 animate-in fade-in duration-500">
      {/* Header & Controls */}
      <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-3 bg-[#1e2329]/80 backdrop-blur-md p-3 rounded-xl border border-gray-800 shadow-2xl">
        <div className="flex items-center gap-3">
          <div className="bg-blue-600/20 p-2 rounded-lg border border-blue-500/30">
            <span className="text-lg">📈</span>
          </div>
          <div>
            <h1 className="text-lg font-black tracking-tight flex items-center gap-2 text-gray-100">
              TACTICAL TERMINAL
              <span className="text-[9px] bg-green-500/10 text-green-500 border border-green-500/20 px-1.5 py-0.5 rounded font-bold animate-pulse">LIVE</span>
            </h1>
            <div className="flex items-center gap-2 text-[10px] font-mono">
              <span className="text-blue-400 font-bold opacity-80">{exchange.toUpperCase()}</span>
              <span className="text-gray-700">:</span>
              <span className="text-white font-black">{symbol}</span>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Symbol & Exchange Selectors */}
          <div className="flex bg-black/60 p-1 rounded-lg border border-gray-700/50 items-center">
            <select
              value={exchange}
              onChange={(e) => setExchange(e.target.value)}
              className="bg-transparent text-[10px] font-black text-gray-400 outline-none px-2 py-1 cursor-pointer hover:text-white transition-colors"
            >
              <option value="bybit">BYBIT</option>
            </select>
            <div className="w-[1px] h-3 bg-gray-800 mx-1"></div>
            <select
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className="bg-transparent text-[11px] font-black text-blue-400 outline-none px-2 py-1 min-w-[100px] cursor-pointer hover:brightness-125 transition-all"
            >
              {filteredMarkets?.map(m => (
                <option key={m.id} value={m.symbol}>{m.symbol}</option>
              ))}
            </select>
          </div>

          {/* Timeframe Selector */}
          <div className="flex bg-black/60 p-1 rounded-lg border border-gray-700/50">
            {['1m', '5m', '15m', '1h', '4h', '1d'].map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-3 py-1 text-[10px] font-black rounded transition-all ${
                  timeframe === tf
                    ? 'bg-blue-600 text-white shadow-[0_0_10px_rgba(37,99,235,0.4)]'
                    : 'text-gray-600 hover:text-gray-400'
                }`}
              >
                {tf.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-4">
        {/* Main Chart Area */}
        <div className="xl:col-span-3 space-y-4">
          {/* Indicators Toggle Bar */}
          <div className="flex flex-wrap gap-2 items-center bg-[#161a1e] p-2 rounded-lg border border-gray-800/50">
            <span className="text-[10px] font-bold text-gray-500 uppercase px-2 tracking-widest">Visibility:</span>
            {[
              { key: 'ma20', label: 'MA20', color: 'text-blue-400' },
              { key: 'ma60', label: 'MA60', color: 'text-amber-500' },
              { key: 'ma200', label: 'MA200', color: 'text-purple-500' },
              { key: 'bb', label: 'BB', color: 'text-cyan-400' },
              { key: 'macd', label: 'MACD', color: 'text-gray-400' },
              { key: 'oi', label: 'OI', color: 'text-purple-400' },
              { key: 'depth', label: 'DEPTH', color: 'text-teal-400' }
            ].map((ind) => (
              <button
                key={ind.key}
                onClick={() => toggleIndicator(ind.key as any)}
                className={`px-3 py-1 rounded text-[10px] font-black border transition-all ${
                  visibleIndicators[ind.key as keyof typeof visibleIndicators]
                    ? `bg-gray-800 ${ind.color} border-gray-700 shadow-inner`
                    : 'bg-transparent text-gray-600 border-transparent grayscale'
                }`}
              >
                {ind.label}
              </button>
            ))}
          </div>

          <div className="card h-[600px] overflow-hidden">
            {dataWithIndicators && (
              <MemoizedLightweightCandlestickChart 
                data={dataWithIndicators} 
                cvdData={cvdData?.map(d => ({ time: d.time, cvd: d.cvd }))}
                liquidations={liquidations}
                visibleIndicators={visibleIndicators}
                onChartCreate={(chart) => onChartCreate('main', chart)}
                key={`${exchange}-${symbol}-${timeframe}`}
              />
            )}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {visibleIndicators.macd && dataWithIndicators && (
              <div className="card h-[300px]">
                <h2 className="text-[10px] font-bold text-gray-500 mb-2 tracking-widest uppercase">MACD Convergence/Divergence</h2>
                <MemoizedMACDChart 
                  data={dataWithIndicators} 
                  onChartCreate={(chart) => onChartCreate('macd', chart)}
                  key={`macd-${exchange}-${symbol}-${timeframe}`}
                />
              </div>
            )}
            {visibleIndicators.oi && openInterest && (
              <div className="card h-[300px]">
                <h2 className="text-[10px] font-bold text-gray-500 mb-2 tracking-widest uppercase">Open Interest (Derivatives)</h2>
                <MemoizedOpenInterestChart 
                  data={openInterest} 
                  onChartCreate={(chart) => onChartCreate('oi', chart)}
                  key={`oi-${exchange}-${symbol}`}
                />
              </div>
            )}
          </div>
        </div>

        {/* Sidebar Intel */}
        <div className="space-y-4 flex flex-col h-full">
          <div className="card flex-none">
            <h2 className="text-[10px] font-bold text-gray-500 mb-4 tracking-widest uppercase">Quick Statistics</h2>
            {dataWithIndicators && <MemoizedIndicatorStats data={dataWithIndicators} />}
          </div>

          <div className="h-[400px]">
            <SignalTimeline symbol={symbol} limit={20} />
          </div>

          <div className="card flex-none">
             <AlertsManager 
                currentSymbol={symbol} 
                currentPrice={dataWithIndicators && dataWithIndicators.length > 0 
                  ? dataWithIndicators[dataWithIndicators.length - 1].close 
                  : 0} 
              />
          </div>
        </div>
      </div>
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