'use client'

import { useState, useMemo, memo, useRef, useCallback, useEffect, Suspense } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useRouter, useSearchParams, usePathname } from 'next/navigation'
import type { IChartApi, LogicalRange } from 'lightweight-charts'
import { 
  fetchOHLCV, 
  fetchMarkets, 
  fetchFundingRate, 
  fetchOpenInterest,
  fetchLatestOrderbook,
  fetchCVD,
  fetchLiquidations,
  fetchFearGreed
} from '@/lib/api-client'
import { calculateAllIndicators } from '@/lib/indicators'
import { LightweightCandlestickChart } from '@/components/charts/LightweightCandlestickChart'
import { MACDChart } from '@/components/charts/MACDChart'
import { FundingRateChart } from '@/components/charts/FundingRateChart'
import { OpenInterestChart } from '@/components/charts/OpenInterestChart'
import { DepthChart } from '@/components/charts/DepthChart'
import { AlertsManager } from '@/components/AlertsManager'
import { SignalTimeline } from '@/components/SignalTimeline'
import { QUERY_PROFILES } from '@/lib/queryProfiles'
import type { OpenInterest } from '@/types/market'

// Memoize components to prevent re-renders when visibility toggles
const MemoizedMACDChart = memo(MACDChart)
const MemoizedFundingRateChart = memo(FundingRateChart)
const MemoizedOpenInterestChart = memo(OpenInterestChart)
const MemoizedDepthChart = memo(DepthChart)
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
    fractal: false,
    vpvr: false,
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
    ...QUERY_PROFILES.high,
  })

  const { data: cvdData } = useQuery({
    queryKey: ['cvd', exchange, symbol, timeframe],
    queryFn: () => fetchCVD(exchange, symbol, timeframe, 500),
    ...QUERY_PROFILES.high,
  })

  const { data: liquidations } = useQuery({
    queryKey: ['liquidations', exchange, symbol],
    queryFn: () => fetchLiquidations(exchange, symbol, 100),
    ...QUERY_PROFILES.high,
  })

  const { data: orderbook } = useQuery({
    queryKey: ['orderbook', exchange, symbol],
    queryFn: () => fetchLatestOrderbook(exchange, symbol),
    ...QUERY_PROFILES.ultra,
    enabled: visibleIndicators.depth,
  })

  const { data: fundingRate } = useQuery({
    queryKey: ['funding-rate', exchange, symbol],
    queryFn: () => fetchFundingRate(exchange, symbol, 100),
    ...QUERY_PROFILES.medium,
    enabled: ['bybit', 'binance', 'okx'].includes((exchange || '').toLowerCase()),
  })

  const { data: openInterest } = useQuery({
    queryKey: ['open-interest', exchange, symbol],
    queryFn: () => fetchOpenInterest(exchange, symbol, 500),
    ...QUERY_PROFILES.medium,
    enabled: ['bybit', 'binance', 'okx'].includes((exchange || '').toLowerCase()),
  })

  const { data: fearGreed } = useQuery({
    queryKey: ['fear-greed'],
    queryFn: fetchFearGreed,
    ...QUERY_PROFILES.slow,
  })

  // ✅ 合併與計算指標 (必須在 useEffect 之前定義)
  const oiSeries = useMemo(() => {
    if (!openInterest || openInterest.length === 0) return []
    return openInterest
      .map(oi => ({
        t: new Date(oi.timestamp).getTime(),
        open_interest: oi.open_interest,
        open_interest_usd: oi.open_interest_usd
      }))
      .sort((a, b) => a.t - b.t)
  }, [openInterest])

  const frSeries = useMemo(() => {
    if (!fundingRate || fundingRate.length === 0) return []
    return fundingRate
      .map(fr => ({
        t: new Date(fr.timestamp).getTime(),
        funding_rate: fr.funding_rate
      }))
      .sort((a, b) => a.t - b.t)
  }, [fundingRate])

  const dataWithIndicators = useMemo(() => {
    if (!ohlcv || ohlcv.length === 0) return null
    
    // 1. 基本指標計算
    const indicators = calculateAllIndicators(ohlcv)

    let oiIdx = 0
    let frIdx = 0
    const oiWindowMs = timeframe === '1m'
      ? 15 * 60 * 1000
      : timeframe === '5m'
        ? 30 * 60 * 1000
        : timeframe === '15m'
          ? 60 * 60 * 1000
          : timeframe === '1h'
            ? 3 * 60 * 60 * 1000
            : timeframe === '4h'
              ? 8 * 60 * 60 * 1000
              : 24 * 60 * 60 * 1000
    const frWindowMs = 14400000

    // 2. 對齊 OI 與 Funding Rate (如果有)
    return indicators.map(d => {
      const ts = new Date(d.timestamp).getTime()

      let oi_val = undefined
      let oi_usd = undefined
      if (oiSeries.length > 0) {
        while (oiIdx + 1 < oiSeries.length && oiSeries[oiIdx + 1].t <= ts) {
          oiIdx += 1
        }
        const current = oiSeries[oiIdx]
        const next = oiIdx + 1 < oiSeries.length ? oiSeries[oiIdx + 1] : null
        const candidate = next && Math.abs(next.t - ts) < Math.abs(current.t - ts) ? next : current
        if (Math.abs(candidate.t - ts) <= oiWindowMs) {
          oi_val = candidate.open_interest
          oi_usd = candidate.open_interest_usd || undefined
        }
      }

      let fr_val = undefined
      if (frSeries.length > 0) {
        while (frIdx + 1 < frSeries.length && frSeries[frIdx + 1].t <= ts) {
          frIdx += 1
        }
        const current = frSeries[frIdx]
        const next = frIdx + 1 < frSeries.length ? frSeries[frIdx + 1] : null
        const candidate = next && Math.abs(next.t - ts) < Math.abs(current.t - ts) ? next : current
        if (Math.abs(candidate.t - ts) < frWindowMs) {
          fr_val = candidate.funding_rate
        }
      }

      return {
        ...d,
        open_interest: oi_val,
        open_interest_usd: oi_usd,
        funding_rate: fr_val
      }
    })
  }, [ohlcv, oiSeries, frSeries, timeframe])

  // 圖表引用管理
  const chartsRef = useRef<Map<string, IChartApi>>(new Map())
  const syncHandlersRef = useRef<Map<string, (range: LogicalRange | null) => void>>(new Map())
  const isSyncingRef = useRef(false)
  const mainChartId = 'main'

  const syncAllChartsFromMain = useCallback(() => {
    const charts = chartsRef.current
    const mainChart = charts.get(mainChartId)
    if (!mainChart) return

    const mainLogicalRange = mainChart.timeScale().getVisibleLogicalRange()
    const mainTimeRange = mainChart.timeScale().getVisibleRange()
    if (!mainLogicalRange && !mainTimeRange) return

    charts.forEach((chart, id) => {
      if (id === mainChartId) return
      try {
        if (mainLogicalRange) {
          chart.timeScale().setVisibleLogicalRange(mainLogicalRange)
        } else if (mainTimeRange) {
          chart.timeScale().setVisibleRange(mainTimeRange)
        }
      } catch (e) {
        // ignore destroyed or not-ready charts
      }
    })
  }, [])

  const onChartCreate = useCallback((id: string, chart: IChartApi) => {
    console.log(`[Chart Sync] Registering chart: ${id}`);
    chartsRef.current.set(id, chart)

    chart.timeScale().applyOptions({
      timeVisible: true,
      secondsVisible: false,
      rightOffset: 0,
    })

    // 新圖建立後，強制對齊到主圖可視範圍
    requestAnimationFrame(() => {
      syncAllChartsFromMain()
    })
  }, [syncAllChartsFromMain])

  // 同步邏輯 - 強化版 (解決不同步問題)
  useEffect(() => {
    const charts = chartsRef.current
    if (charts.size === 0) return

    // 1. 先徹底清理所有舊的監聽器
    charts.forEach((chart, id) => {
      const oldHandler = syncHandlersRef.current.get(id)
      if (oldHandler) {
        try { chart.timeScale().unsubscribeVisibleLogicalRangeChange(oldHandler) } catch (e) {}
      }
    })
    syncHandlersRef.current.clear()

    // 2. 定義統一的同步處理器
    const handleSync = (sourceId: string, range: LogicalRange | null) => {
      if (!range || isSyncingRef.current) return
      isSyncingRef.current = true
      
      charts.forEach((chart, id) => {
        if (id !== sourceId) {
          try {
            chart.timeScale().setVisibleLogicalRange(range)
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
      const handler = (range: LogicalRange | null) => handleSync(id, range)
      syncHandlersRef.current.set(id, handler)
      chart.timeScale().subscribeVisibleLogicalRangeChange(handler)
    })

    return () => {
      charts.forEach((chart, id) => {
        const handler = syncHandlersRef.current.get(id)
        if (handler) {
          try { chart.timeScale().unsubscribeVisibleLogicalRangeChange(handler) } catch (e) {}
        }
      })
    }
  }, [visibleIndicators]) // 僅在顯示狀態改變時重新綁定同步

  // 在主要資料或顯示狀態變更後，主圖可視範圍可能更新；主動再同步一次避免初始錯位
  useEffect(() => {
    requestAnimationFrame(() => {
      syncAllChartsFromMain()
    })
  }, [
    exchange,
    symbol,
    timeframe,
    visibleIndicators.macd,
    visibleIndicators.oi,
    dataWithIndicators,
    openInterest,
    syncAllChartsFromMain,
  ])

  const filteredMarkets = markets?.filter(m => m.exchange === exchange)

  const toggleIndicator = (key: keyof typeof visibleIndicators) => {
    setVisibleIndicators(prev => ({ ...prev, [key]: !prev[key] }))
  }

  const fearGreedTone = useMemo(() => {
    const value = fearGreed?.value
    if (value === undefined || value === null) return 'text-gray-400'
    if (value <= 24) return 'text-red-400'
    if (value <= 44) return 'text-orange-400'
    if (value <= 55) return 'text-yellow-400'
    if (value <= 75) return 'text-green-400'
    return 'text-emerald-400'
  }, [fearGreed])

  const quickStats = useMemo(() => {
    if (!dataWithIndicators || dataWithIndicators.length === 0) return null
    const latest = dataWithIndicators[dataWithIndicators.length - 1]
    const price = latest.close
    const rsi = latest.rsi_14
    const macd = latest.macd
    const macdSignal = latest.macd_signal
    const ma20Gap = latest.sma_20 ? ((price / latest.sma_20 - 1) * 100) : null
    const ma60Gap = latest.sma_60 ? ((price / latest.sma_60 - 1) * 100) : null
    const macdBias = macd !== undefined && macdSignal !== undefined
      ? (macd > macdSignal ? 'Bullish' : 'Bearish')
      : 'N/A'

    return {
      price,
      rsi,
      ma20Gap,
      ma60Gap,
      macdBias,
      updatedAt: latest.timestamp,
    }
  }, [dataWithIndicators])

  // 用主 K 線時間軸對齊 OI，確保 K / MACD / OI 三圖的 x 軸範圍一致
  const alignedOpenInterest = useMemo<OpenInterest[]>(() => {
    if (!ohlcv || ohlcv.length === 0 || !openInterest || openInterest.length === 0) return []

    const oiSorted = [...openInterest]
      .filter((d) => d.timestamp && d.open_interest != null)
      .map((d) => ({
        ...d,
        t: new Date(d.timestamp).getTime(),
        open_interest: Number(d.open_interest),
      }))
      .filter((d) => Number.isFinite(d.t) && Number.isFinite(d.open_interest))
      .sort((a, b) => a.t - b.t)

    if (oiSorted.length === 0) return []

    const maxStalenessMs = timeframe === '1m'
      ? 4 * 60 * 60 * 1000
      : timeframe === '5m'
        ? 6 * 60 * 60 * 1000
        : timeframe === '15m'
          ? 8 * 60 * 60 * 1000
          : timeframe === '1h'
            ? 12 * 60 * 60 * 1000
            : timeframe === '4h'
              ? 24 * 60 * 60 * 1000
              : 48 * 60 * 60 * 1000

    const aligned: OpenInterest[] = []
    let oiIdx = 0
    let lastKnown: (typeof oiSorted)[number] | null = null

    for (const candle of ohlcv) {
      const ts = new Date(candle.timestamp).getTime()
      if (!Number.isFinite(ts)) continue

      while (oiIdx < oiSorted.length && oiSorted[oiIdx].t <= ts) {
        lastKnown = oiSorted[oiIdx]
        oiIdx += 1
      }

      if (!lastKnown) continue
      if (ts - lastKnown.t > maxStalenessMs) continue

      aligned.push({
        timestamp: candle.timestamp,
        open_interest: lastKnown.open_interest,
        open_interest_usd: lastKnown.open_interest_usd ?? null,
        open_interest_change_24h: lastKnown.open_interest_change_24h ?? null,
        open_interest_change_pct: lastKnown.open_interest_change_pct ?? null,
        price: candle.close ?? lastKnown.price ?? null,
        volume_24h: lastKnown.volume_24h ?? null,
      })
    }

    return aligned.length > 0
      ? aligned
      : oiSorted.map((d) => ({
          timestamp: d.timestamp,
          open_interest: d.open_interest,
          open_interest_usd: d.open_interest_usd ?? null,
          open_interest_change_24h: d.open_interest_change_24h ?? null,
          open_interest_change_pct: d.open_interest_change_pct ?? null,
          price: d.price ?? null,
          volume_24h: d.volume_24h ?? null,
        }))
  }, [ohlcv, openInterest, timeframe])

  const marketRegime = useMemo(() => {
    if (!quickStats) return { label: 'No Data', tone: 'text-gray-400 border-gray-700' }

    const rsi = quickStats.rsi ?? null
    const isBullish = quickStats.macdBias === 'Bullish'
    const isBearish = quickStats.macdBias === 'Bearish'
    const fg = fearGreed?.value ?? null

    if (rsi !== null && rsi >= 60 && isBullish && fg !== null && fg >= 55) {
      return { label: 'Risk-On', tone: 'text-green-400 border-green-500/40' }
    }
    if (rsi !== null && rsi <= 40 && isBearish && fg !== null && fg <= 45) {
      return { label: 'Risk-Off', tone: 'text-red-400 border-red-500/40' }
    }
    return { label: 'Mixed', tone: 'text-yellow-400 border-yellow-500/40' }
  }, [quickStats, fearGreed])

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

      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_360px] gap-4">
        {/* Main Chart Area */}
        <div className="space-y-4">
          {/* Indicators Toggle Bar */}
          <div className="flex flex-wrap gap-2 items-center bg-[#161a1e] p-2 rounded-lg border border-gray-800/50">
            <span className="text-[10px] font-bold text-gray-500 uppercase px-2 tracking-widest">Visibility:</span>
            {[
              { key: 'ma20', label: 'MA20', color: 'text-blue-400' },
              { key: 'ma60', label: 'MA60', color: 'text-amber-500' },
              { key: 'ma200', label: 'MA200', color: 'text-purple-500' },
              { key: 'bb', label: 'BB', color: 'text-cyan-400' },
              { key: 'fractal', label: 'FRACTAL', color: 'text-lime-400' },
              { key: 'vpvr', label: 'VPVR', color: 'text-orange-400' },
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
                timeframe={timeframe}
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
                  timeframe={timeframe}
                  key={`macd-${exchange}-${symbol}-${timeframe}`}
                />
              </div>
            )}
            {visibleIndicators.oi && alignedOpenInterest.length > 0 && (
              <div className="card h-[300px]">
                <h2 className="text-[10px] font-bold text-gray-500 mb-2 tracking-widest uppercase">Open Interest (Derivatives)</h2>
                <MemoizedOpenInterestChart 
                  data={alignedOpenInterest} 
                  onChartCreate={(chart) => onChartCreate('oi', chart)}
                  timeframe={timeframe}
                  key={`oi-${exchange}-${symbol}-${timeframe}`}
                />
              </div>
            )}
          </div>
        </div>

        {/* Sidebar Intel */}
        <div className="space-y-4 flex flex-col h-full min-w-0">
          <div className="card flex-none px-4 py-4 overflow-hidden border border-gray-800 rounded-xl">
            <h2 className="text-[11px] font-bold text-gray-500 mb-3 tracking-widest uppercase">Market Intel</h2>
            <div className="grid grid-cols-2 gap-2">
              <div className="rounded border border-gray-800 bg-gray-900/40 p-3">
                <div className="text-[10px] text-gray-500 uppercase">Price</div>
                <div className="text-sm font-black text-blue-400">
                  {quickStats ? `$${Number(quickStats.price).toLocaleString()}` : '--'}
                </div>
              </div>
              <div className="rounded border border-gray-800 bg-gray-900/40 p-3">
                <div className="text-[10px] text-gray-500 uppercase">RSI 14</div>
                <div className="text-sm font-black text-gray-100">
                  {quickStats?.rsi !== undefined && quickStats?.rsi !== null
                    ? quickStats.rsi.toFixed(1)
                    : '--'}
                </div>
              </div>
              <div className="rounded border border-gray-800 bg-gray-900/40 p-3">
                <div className="text-[10px] text-gray-500 uppercase">vs MA20</div>
                <div className={`text-sm font-black ${
                  quickStats?.ma20Gap !== null && quickStats?.ma20Gap !== undefined
                    ? (quickStats.ma20Gap >= 0 ? 'text-green-400' : 'text-red-400')
                    : 'text-gray-100'
                }`}>
                  {quickStats?.ma20Gap !== null && quickStats?.ma20Gap !== undefined
                    ? `${quickStats.ma20Gap >= 0 ? '+' : ''}${quickStats.ma20Gap.toFixed(2)}%`
                    : '--'}
                </div>
              </div>
              <div className="rounded border border-gray-800 bg-gray-900/40 p-3">
                <div className="text-[10px] text-gray-500 uppercase">MACD Bias</div>
                <div className={`text-sm font-black ${
                  quickStats?.macdBias === 'Bullish' ? 'text-green-400' :
                  quickStats?.macdBias === 'Bearish' ? 'text-red-400' : 'text-gray-100'
                }`}>
                  {quickStats?.macdBias ?? '--'}
                </div>
              </div>
            </div>
            <div className="mt-2 flex flex-col gap-2 text-[11px] text-gray-500">
              <div className={`px-2 py-1 rounded border ${marketRegime.tone}`}>
                Regime: {marketRegime.label}
              </div>
              <div className="font-mono text-gray-400 break-all leading-tight">
                Price TS: {quickStats?.updatedAt ? new Date(quickStats.updatedAt).toLocaleString('zh-TW', {
                  month: '2-digit',
                  day: '2-digit',
                  hour: '2-digit',
                  minute: '2-digit',
                  hour12: false,
                }) : '--'}
              </div>
            </div>
            <div className="mt-3 pt-3 border-t border-gray-800/80 flex items-end justify-between gap-3">
              <div className="min-w-0">
                <div className="text-[10px] text-gray-500 uppercase tracking-wider">Fear & Greed</div>
                <div className={`text-xl font-black ${fearGreedTone}`}>
                  {fearGreed?.value ?? '--'}
                </div>
              </div>
              <div className="text-right min-w-0">
                <div className={`text-xs font-bold uppercase ${fearGreedTone} truncate`}>
                  {fearGreed?.classification ?? 'N/A'}
                </div>
                <div className="text-[10px] text-gray-500 mt-1 font-mono leading-tight">
                  {fearGreed?.timestamp
                    ? new Date(fearGreed.timestamp).toLocaleString('zh-TW', {
                        month: '2-digit',
                        day: '2-digit',
                        hour: '2-digit',
                        minute: '2-digit',
                        hour12: false,
                      })
                    : 'No data'}
                </div>
              </div>
            </div>
          </div>

          <div className="h-[360px]">
            <SignalTimeline symbol={symbol} limit={20} />
          </div>

          <div className="flex-none">
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
