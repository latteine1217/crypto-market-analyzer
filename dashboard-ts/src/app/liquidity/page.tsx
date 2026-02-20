'use client'

import { useState, useMemo } from 'react'
import { clsx } from 'clsx'
import { useQuery } from '@tanstack/react-query'
import { fetchLatestOrderbook, fetchMarkets, fetchOrderSizeAnalytics, fetchOBI } from '@/lib/api-client'
import { DepthChart } from '@/components/charts/DepthChart'
import { OrderSizeChart } from '@/components/charts/OrderSizeChart'
import { CVDChart } from '@/components/charts/CVDChart'
import { OBIChart } from '@/components/charts/OBIChart'
import FundingRateHeatmap from '@/components/charts/FundingRateHeatmap'
import type { OrderBookLevel } from '@/types/market'
import { QUERY_PROFILES } from '@/lib/queryProfiles'

export default function LiquidityPage() {
  const [exchange, setExchange] = useState('bybit')
  const [symbol, setSymbol] = useState('BTCUSDT')
  const orderbookLevels = 100

  const { data: markets } = useQuery({
    queryKey: ['markets'],
    queryFn: fetchMarkets,
  })

  const { data: orderSizeData } = useQuery({
    queryKey: ['analytics-order-size', exchange, symbol],
    queryFn: () => fetchOrderSizeAnalytics(exchange, symbol),
    ...QUERY_PROFILES.low,
  })

  const { data: orderbook, isLoading } = useQuery({
    queryKey: ['orderbook-latest', exchange, symbol],
    queryFn: () => fetchLatestOrderbook(exchange, symbol),
    ...QUERY_PROFILES.high,
  })

  const { data: snapshots } = useQuery({
    queryKey: ['orderbook-history', exchange, symbol],
    queryFn: () => fetchOBI(exchange, symbol, 1),
    ...QUERY_PROFILES.high,
  })

  const latestOBI = snapshots?.[0]?.obi || 0

  const filteredMarkets = markets?.filter(m => m.exchange === exchange)

  const formatUsd = (value: number) => {
    const abs = Math.abs(value)
    if (abs >= 1e9) return `$${(value / 1e9).toFixed(2)}B`
    if (abs >= 1e6) return `$${(value / 1e6).toFixed(2)}M`
    if (abs >= 1e3) return `$${(value / 1e3).toFixed(2)}K`
    return `$${value.toFixed(2)}`
  }

  // 計算訂單簿統計資料
  const stats = useMemo(() => {
    if (!orderbook) return null
    const totalBidsQty = orderbook.bids?.reduce((sum, b) => sum + Number(b.quantity), 0) || 0
    const totalAsksQty = orderbook.asks?.reduce((sum, a) => sum + Number(a.quantity), 0) || 0
    const totalBidsUsd = orderbook.bids?.reduce((sum, b) => sum + Number(b.price) * Number(b.quantity), 0) || 0
    const totalAsksUsd = orderbook.asks?.reduce((sum, a) => sum + Number(a.price) * Number(a.quantity), 0) || 0

    return {
      totalBidsQty,
      totalAsksQty,
      totalBidsUsd,
      totalAsksUsd,
      bestBid: orderbook.bids?.[0]?.price || 0,
      bestAsk: orderbook.asks?.[0]?.price || 0,
      spread: orderbook.asks && orderbook.bids 
        ? Number(orderbook.asks[0]?.price) - Number(orderbook.bids[0]?.price)
        : 0,
    }
  }, [orderbook])

  const spreadPercent = useMemo(() => 
    stats ? ((stats.spread / stats.bestAsk) * 100).toFixed(4) : '0'
  , [stats])

  const spreadBps = useMemo(() =>
    stats && stats.bestAsk > 0 ? (stats.spread / stats.bestAsk) * 10000 : 0
  , [stats])

  const liquiditySkewPct = useMemo(() => {
    if (!stats) return 0
    const total = stats.totalBidsUsd + stats.totalAsksUsd
    if (total <= 0) return 0
    return ((stats.totalBidsUsd - stats.totalAsksUsd) / total) * 100
  }, [stats])

  const liquidityRegime = useMemo(() => {
    if (!stats) return { label: 'NO DATA', tone: 'text-gray-400 border-gray-700' }

    if (spreadBps <= 2 && latestOBI > 0.25 && liquiditySkewPct > 8) {
      return { label: 'BID SUPPORT', tone: 'text-green-400 border-green-500/30' }
    }
    if (spreadBps <= 2 && latestOBI < -0.25 && liquiditySkewPct < -8) {
      return { label: 'ASK PRESSURE', tone: 'text-red-400 border-red-500/30' }
    }
    if (spreadBps > 6) {
      return { label: 'THIN BOOK', tone: 'text-amber-400 border-amber-500/30' }
    }
    return { label: 'BALANCED', tone: 'text-blue-400 border-blue-500/30' }
  }, [stats, spreadBps, latestOBI, liquiditySkewPct])

  const orderbookAgeSec = useMemo(() => {
    if (!orderbook?.timestamp) return null
    const ts = new Date(orderbook.timestamp).getTime()
    if (Number.isNaN(ts)) return null
    return Math.max(0, (Date.now() - ts) / 1000)
  }, [orderbook?.timestamp])

  // 計算累積量（用於視覺化）
  const processedData = useMemo(() => {
    if (!orderbook) return { bids: [], asks: [], maxCumulative: 0 }
    
    const topBids = orderbook.bids?.slice(0, orderbookLevels) || []
    const topAsks = orderbook.asks?.slice(0, orderbookLevels) || []
    const bidsWithCumulative: Array<OrderBookLevel & { cumulative: number }> = []
    const asksWithCumulative: Array<OrderBookLevel & { cumulative: number }> = []

    let bidCum = 0
    for (let i = 0; i < topBids.length; i++) {
      const bid = topBids[i]
      bidCum += Number(bid.quantity)
      bidsWithCumulative.push({ ...bid, cumulative: bidCum })
    }

    let askCum = 0
    for (let i = 0; i < topAsks.length; i++) {
      const ask = topAsks[i]
      askCum += Number(ask.quantity)
      asksWithCumulative.push({ ...ask, cumulative: askCum })
    }

    const maxCumulative = Math.max(
      bidsWithCumulative[bidsWithCumulative.length - 1]?.cumulative || 0,
      asksWithCumulative[asksWithCumulative.length - 1]?.cumulative || 0
    )

    return { bids: bidsWithCumulative, asks: asksWithCumulative, maxCumulative }
  }, [orderbook, orderbookLevels])

  const { bids: bidsWithCumulative, asks: asksWithCumulative, maxCumulative } = processedData

  return (
    <div className="max-w-[1600px] mx-auto space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-2xl font-black tracking-tight">LIQUIDITY HUB</h1>
            <span className="bg-blue-500/10 text-blue-500 text-[10px] font-bold px-2 py-0.5 rounded border border-blue-500/20">LIVE MARKET</span>
          </div>
          <p className="text-sm text-gray-500 font-medium">
            這頁回答三件事：盤口流動性在哪裡、主動買賣誰在主導（CVD）、以及槓桿壓力（Funding）。
          </p>
        </div>

        <div className="flex items-center gap-3 bg-[#1e2329] p-1.5 rounded-lg border border-gray-800">
          <select
            value={exchange}
            onChange={(e) => setExchange(e.target.value)}
            className="bg-transparent text-sm font-bold text-gray-300 outline-none px-2 cursor-pointer"
          >
            <option value="bybit">BYBIT</option>
          </select>
          <div className="w-[1px] h-4 bg-gray-700"></div>
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="bg-transparent text-sm font-bold text-blue-400 outline-none px-2 min-w-[120px] cursor-pointer"
          >
            {filteredMarkets?.map(m => (
              <option key={m.id} value={m.symbol}>
                {m.symbol}
              </option>
            ))}
          </select>
        </div>
      </div>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
          <div className="stat-card glow-green">
            <span className="stat-label">Best Bid</span>
            <span className="stat-value text-[#00c073]">${Number(stats.bestBid).toLocaleString()}</span>
          </div>
          <div className="stat-card glow-red">
            <span className="stat-label">Best Ask</span>
            <span className="stat-value text-[#f6465d]">${Number(stats.bestAsk).toLocaleString()}</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Spread</span>
            <div className="flex items-baseline gap-2">
              <span className="stat-value">${stats.spread.toFixed(2)}</span>
              <span className="text-[10px] text-gray-500 font-bold">{spreadPercent}%</span>
            </div>
          </div>
          <div className="stat-card">
            <span className="stat-label">Bid Liquidity (USD)</span>
            <span className="stat-value text-[#00c073]">{formatUsd(stats.totalBidsUsd)}</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Ask Liquidity (USD)</span>
            <span className="stat-value text-[#f6465d]">{formatUsd(stats.totalAsksUsd)}</span>
          </div>
          <div className={clsx(
            "stat-card",
            latestOBI > 0.3 ? "border-green-500/30 bg-green-500/5" : 
            latestOBI < -0.3 ? "border-red-500/30 bg-red-500/5" : ""
          )}>
            <span className="stat-label">Book Imbalance</span>
            <div className="flex items-baseline gap-2">
              <span className={clsx(
                "stat-value",
                latestOBI > 0.1 ? "text-[#00c073]" : 
                latestOBI < -0.1 ? "text-[#f6465d]" : "text-gray-400"
              )}>
                {(latestOBI * 100).toFixed(1)}%
              </span>
              <span className="text-[10px] text-gray-500 font-bold">
                {latestOBI > 0.3 ? 'BIDS UP' : latestOBI < -0.3 ? 'ASKS DOWN' : 'NEUTRAL'}
              </span>
            </div>
          </div>
        </div>
      )}

      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className={`card p-4 border ${liquidityRegime.tone}`}>
            <div className="text-[10px] text-gray-500 uppercase tracking-widest mb-1">Liquidity Regime</div>
            <div className={`text-lg font-black ${liquidityRegime.tone.split(' ')[0]}`}>{liquidityRegime.label}</div>
            <div className="text-[11px] text-gray-500 mt-1">基於 spread、OBI 與 bid/ask notional skew</div>
          </div>
          <div className="card p-4">
            <div className="text-[10px] text-gray-500 uppercase tracking-widest mb-1">Spread (bps)</div>
            <div className={clsx(
              "text-lg font-black",
              spreadBps <= 2 ? "text-green-400" : spreadBps > 6 ? "text-amber-400" : "text-gray-200"
            )}>
              {spreadBps.toFixed(2)} bps
            </div>
            <div className="text-[11px] text-gray-500 mt-1">{spreadBps <= 2 ? 'Tight execution window' : 'Slippage risk rising'}</div>
          </div>
          <div className="card p-4">
            <div className="text-[10px] text-gray-500 uppercase tracking-widest mb-1">Bid/Ask Skew</div>
            <div className={clsx(
              "text-lg font-black",
              liquiditySkewPct > 0 ? "text-green-400" : liquiditySkewPct < 0 ? "text-red-400" : "text-gray-200"
            )}>
              {liquiditySkewPct > 0 ? '+' : ''}{liquiditySkewPct.toFixed(1)}%
            </div>
            <div className="text-[11px] text-gray-500 mt-1">Notional imbalance across visible book</div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 space-y-6">
          <div className="card h-[450px]">
            <DepthChart orderbook={orderbook!} />
          </div>
          
          <div className="space-y-6">
            <div className="h-[380px]">
              <CVDChart exchange={exchange} symbol={symbol} />
            </div>
            <div className="h-[380px]">
              <OBIChart exchange={exchange} symbol={symbol} />
            </div>
            <div className="h-[380px]">
              <OrderSizeChart data={orderSizeData || []} symbol={symbol} />
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <FundingRateHeatmap />

          {/* Orderbook List Section */}
          <div className="card h-full overflow-hidden flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold flex items-center gap-2">
                <span className="w-1.5 h-3 bg-blue-500 rounded-full"></span>
                ORDER BOOK
              </h2>
              <span className="text-[10px] text-gray-500 font-mono">L2 REALTIME</span>
            </div>
            
            <div className="grid grid-cols-2 gap-px bg-gray-800/50 flex-1 overflow-hidden">
              <div className="bg-[#161a1e] p-2 flex flex-col h-full">
                <div className="flex justify-between text-[10px] text-gray-500 font-bold mb-2 uppercase">
                  <span>Price</span>
                  <span>Size</span>
                </div>
                <div className="flex-1 overflow-y-auto custom-scrollbar space-y-0.5">
                  {isLoading && bidsWithCumulative.length === 0 && (
                    <div className="text-[10px] text-gray-500 p-2">Loading bids...</div>
                  )}
                  {bidsWithCumulative.map((bid, i) => (
                    <div key={i} className="relative group h-6">
                      <div className="absolute inset-y-0 right-0 bg-green-500/10 group-hover:bg-green-500/20 transition-colors" style={{ width: `${(bid.cumulative / maxCumulative) * 100}%` }} />
                      <div className="relative flex justify-between text-[11px] font-mono h-full items-center px-1">
                        <span className="text-[#00c073] font-bold">{Number(bid.price).toFixed(1)}</span>
                        <span className="text-gray-300">{Number(bid.quantity).toFixed(3)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-[#161a1e] p-2 flex flex-col h-full">
                <div className="flex justify-between text-[10px] text-gray-500 font-bold mb-2 uppercase">
                  <span>Price</span>
                  <span>Size</span>
                </div>
                <div className="flex-1 overflow-y-auto custom-scrollbar space-y-0.5">
                  {isLoading && asksWithCumulative.length === 0 && (
                    <div className="text-[10px] text-gray-500 p-2">Loading asks...</div>
                  )}
                  {asksWithCumulative.map((ask, i) => (
                    <div key={i} className="relative group h-6">
                      <div className="absolute inset-y-0 left-0 bg-red-500/10 group-hover:bg-red-500/20 transition-colors" style={{ width: `${(ask.cumulative / maxCumulative) * 100}%` }} />
                      <div className="relative flex justify-between text-[11px] font-mono h-full items-center px-1">
                        <span className="text-[#f6465d] font-bold">{Number(ask.price).toFixed(1)}</span>
                        <span className="text-gray-300">{Number(ask.quantity).toFixed(3)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            
            <div className="mt-4 pt-3 border-t border-gray-800 flex justify-between items-center text-[10px] text-gray-500 font-mono">
               <span>DEPTH: TOP {orderbookLevels}</span>
               <span>
                 {orderbookAgeSec === null ? '--' : `AGE ${orderbookAgeSec.toFixed(1)}s`} • {orderbook?.timestamp ? new Date(orderbook.timestamp).toLocaleTimeString() : '--:--:--'}
               </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
