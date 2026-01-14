'use client'

import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchLatestOrderbook, fetchMarkets, fetchOrderSizeAnalytics } from '@/lib/api-client'
import { DepthChart } from '@/components/charts/DepthChart'
import { OrderSizeChart } from '@/components/charts/OrderSizeChart'
import type { OrderBookLevel } from '@/types/market'

export default function LiquidityPage() {
  const [exchange, setExchange] = useState('binance')
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
    
    const topBids = orderbook.bids?.slice(0, 20) || []
    const topAsks = orderbook.asks?.slice(0, 20) || []

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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-2">Liquidity Analysis</h1>
          <p className="text-gray-400">Order book depth visualization</p>
        </div>

        <div className="flex space-x-4">
          <select
            value={exchange}
            onChange={(e) => setExchange(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded px-4 py-2"
          >
            <option value="binance">Binance</option>
            <option value="bybit">Bybit</option>
            <option value="okx">OKX</option>
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
        </div>
      </div>

      {isLoading && (
        <div className="space-y-6 animate-pulse">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-24 bg-gray-800 rounded-xl border border-gray-700"></div>
            ))}
          </div>
          <div className="h-96 bg-gray-800 rounded-xl border border-gray-700"></div>
        </div>
      )}

      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div className="card p-4">
            <div className="text-gray-400 text-sm">Best Bid</div>
            <div className="text-2xl font-bold text-green-500">${Number(stats.bestBid).toLocaleString()}</div>
          </div>
          <div className="card p-4">
            <div className="text-gray-400 text-sm">Best Ask</div>
            <div className="text-2xl font-bold text-red-500">${Number(stats.bestAsk).toLocaleString()}</div>
          </div>
          <div className="card p-4">
            <div className="text-gray-400 text-sm">Spread</div>
            <div className="text-2xl font-bold">${stats.spread.toFixed(2)}</div>
            <div className="text-xs text-gray-500">{spreadPercent}%</div>
          </div>
          <div className="card p-4">
            <div className="text-gray-400 text-sm">Total Bids</div>
            <div className="text-2xl font-bold text-green-500">{stats.totalBids.toFixed(2)}</div>
          </div>
          <div className="card p-4">
            <div className="text-gray-400 text-sm">Total Asks</div>
            <div className="text-2xl font-bold text-red-500">{stats.totalAsks.toFixed(2)}</div>
          </div>
        </div>
      )}

      {orderbook && (
        <>
          <div className="card">
            <h2 className="card-header">Market Depth Chart</h2>
            <div className="p-4">
              <DepthChart orderbook={orderbook} />
            </div>
          </div>

          <div className="mt-6">
            <OrderSizeChart data={orderSizeData || []} symbol={symbol} />
          </div>

          <div className="card">
            <h2 className="card-header">Order Book (Top 20)</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-6">
            {/* Bids (買單) */}
            <div>
              <h3 className="text-lg font-semibold mb-4 text-green-500">Bids (Buy Orders)</h3>
              <div className="space-y-1">
                {bidsWithCumulative.map((bid, i) => {
                  const widthPercent = (bid.cumulative / maxCumulative) * 100
                  return (
                    <div key={i} className="relative">
                      <div
                        className="absolute inset-0 bg-green-900 opacity-20"
                        style={{ width: `${widthPercent}%` }}
                      />
                      <div className="relative flex justify-between px-3 py-1.5 text-sm">
                        <span className="text-green-400 font-mono">${Number(bid.price).toFixed(2)}</span>
                        <span className="text-gray-300 font-mono">{Number(bid.quantity).toFixed(4)}</span>
                        <span className="text-gray-500 font-mono text-xs">{bid.cumulative.toFixed(2)}</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Asks (賣單) */}
            <div>
              <h3 className="text-lg font-semibold mb-4 text-red-500">Asks (Sell Orders)</h3>
              <div className="space-y-1">
                {asksWithCumulative.map((ask, i) => {
                  const widthPercent = (ask.cumulative / maxCumulative) * 100
                  return (
                    <div key={i} className="relative">
                      <div
                        className="absolute inset-0 bg-red-900 opacity-20"
                        style={{ width: `${widthPercent}%` }}
                      />
                      <div className="relative flex justify-between px-3 py-1.5 text-sm">
                        <span className="text-red-400 font-mono">${Number(ask.price).toFixed(2)}</span>
                        <span className="text-gray-300 font-mono">{Number(ask.quantity).toFixed(4)}</span>
                        <span className="text-gray-500 font-mono text-xs">{ask.cumulative.toFixed(2)}</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          <div className="px-6 pb-4 text-xs text-gray-500">
            <div className="flex justify-between">
              <span>Price | Quantity | Cumulative</span>
              <span>Last update: {orderbook.timestamp ? new Date(orderbook.timestamp).toLocaleString() : 'N/A'}</span>
            </div>
          </div>
        </div>
        </>
      )}

      {!orderbook && !isLoading && (
        <div className="card">
          <p className="text-gray-400 text-center py-12">
            No orderbook data available for this market
          </p>
        </div>
      )}
    </div>
  )
}
