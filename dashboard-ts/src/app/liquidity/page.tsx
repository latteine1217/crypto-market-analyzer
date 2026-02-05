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

export default function LiquidityPage() {
  const [exchange, setExchange] = useState('bybit')
  const [symbol, setSymbol] = useState('BTCUSDT')

  const { data: markets } = useQuery({
    queryKey: ['markets'],
    queryFn: fetchMarkets,
  })

  const { data: orderSizeData } = useQuery({
    queryKey: ['analytics-order-size', exchange, symbol],
    queryFn: () => fetchOrderSizeAnalytics(exchange, symbol),
    refetchInterval: 60000, // Refresh every minute
  })

  const { data: orderbook, isLoading } = useQuery({
    queryKey: ['orderbook-latest', exchange, symbol],
    queryFn: () => fetchLatestOrderbook(exchange, symbol),
    refetchInterval: 2000, // 每 2 秒更新
  })

  const { data: snapshots } = useQuery({
    queryKey: ['orderbook-history', exchange, symbol],
    queryFn: () => fetchOBI(exchange, symbol, 1),
    refetchInterval: 5000,
  })

  const latestOBI = snapshots?.[0]?.obi || 0

  const filteredMarkets = markets?.filter(m => m.exchange === exchange)

  // 計算訂單簿統計資料
  const stats = useMemo(() => {
    if (!orderbook) return null
    return {
      totalBids: orderbook.bids?.reduce((sum, b) => sum + Number(b.quantity), 0) || 0,
      totalAsks: orderbook.asks?.reduce((sum, a) => sum + Number(a.quantity), 0) || 0,
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

  // 計算累積量（用於視覺化）
  const processedData = useMemo(() => {
    if (!orderbook) return { bids: [], asks: [], maxCumulative: 0 }
    
    // 提升展示深度至 50 檔
    const topBids = orderbook.bids?.slice(0, 100) || []
    const topAsks = orderbook.asks?.slice(0, 100) || []

    const bidsWithCumulative = topBids.map((bid, i) => ({
      ...bid,
      cumulative: topBids.slice(0, i + 1).reduce((sum, b) => sum + Number(b.quantity), 0),
    }))

    const asksWithCumulative = topAsks.map((ask, i) => ({
      ...ask,
      cumulative: topAsks.slice(0, i + 1).reduce((sum, a) => sum + Number(a.quantity), 0),
    }))

    const maxCumulative = Math.max(
      bidsWithCumulative[bidsWithCumulative.length - 1]?.cumulative || 0,
      asksWithCumulative[asksWithCumulative.length - 1]?.cumulative || 0
    )

    return { bids: bidsWithCumulative, asks: asksWithCumulative, maxCumulative }
  }, [orderbook])

  const { bids: bidsWithCumulative, asks: asksWithCumulative, maxCumulative } = processedData

  return (
    <div className="max-w-[1600px] mx-auto space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-2xl font-black tracking-tight">LIQUIDITY HUB</h1>
            <span className="bg-blue-500/10 text-blue-500 text-[10px] font-bold px-2 py-0.5 rounded border border-blue-500/20">LIVE MARKET</span>
          </div>
          <p className="text-sm text-gray-500 font-medium">Order flow depth, CVD divergence and OBI monitoring</p>
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

      <FundingRateHeatmap />

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
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
            <span className="stat-label">Bid Liquidity</span>
            <span className="stat-value text-[#00c073]">{stats.totalBids.toLocaleString(undefined, {maximumFractionDigits: 1})}</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Ask Liquidity</span>
            <span className="stat-value text-[#f6465d]">{stats.totalAsks.toLocaleString(undefined, {maximumFractionDigits: 1})}</span>
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

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 space-y-6">
          <div className="card h-[450px]">
            <DepthChart orderbook={orderbook!} />
          </div>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="h-[380px]">
              <CVDChart exchange={exchange} symbol={symbol} />
            </div>
            <div className="h-[380px]">
              <OBIChart exchange={exchange} symbol={symbol} />
            </div>
          </div>
        </div>

        <div className="space-y-6">
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
               <span>LATENCY: 45ms</span>
               <span>{orderbook?.timestamp ? new Date(orderbook.timestamp).toLocaleTimeString() : '--:--:--'}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
