'use client'

import { useMemo, useRef, useEffect, useState } from 'react'
import type { OrderBookSnapshot } from '@/types/market'

interface Props {
  orderbook: OrderBookSnapshot
}

export function DepthChart({ orderbook }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [dimensions, setDimensions] = useState({ width: 0, height: 400 })
  const [hoverData, setHoverData] = useState<{ x: number, y: number, price: number, volume: number, type: 'bid' | 'ask' } | null>(null)

  useEffect(() => {
    if (!containerRef.current) return
    const resizeObserver = new ResizeObserver((entries) => {
      if (entries[0]) {
        setDimensions({
          width: entries[0].contentRect.width,
          height: entries[0].contentRect.height,
        })
      }
    })
    resizeObserver.observe(containerRef.current)
    return () => resizeObserver.disconnect()
  }, [])

  const { points, maxVol, minPrice, maxPrice, spread, midPrice } = useMemo(() => {
    if (!orderbook || !orderbook.bids.length || !orderbook.asks.length) {
      return { points: { bids: [], asks: [] }, maxVol: 0, minPrice: 0, maxPrice: 0, spread: 0, midPrice: 0 }
    }

    // Bids: Processing logic for correct depth chart visualization
    // 1. Sort Descending (High to Low) to calculate cumulative volume starting from Best Bid
    const sortedBidsDesc = [...orderbook.bids].sort((a, b) => Number(b.price) - Number(a.price))
    
    const bidsWithVol: { price: number; volume: number }[] = []
    let bidCumVol = 0
    for (const b of sortedBidsDesc) {
      bidCumVol += Number(b.quantity)
      bidsWithVol.push({ price: Number(b.price), volume: bidCumVol })
    }
    // 2. Reverse to Ascending (Low to High) for SVG path drawing (X-axis)
    const bidPoints = bidsWithVol.reverse()

    // Asks: Processing logic
    // 1. Sort Ascending (Low to High) - Cumulative starts from Best Ask
    const sortedAsksAsc = [...orderbook.asks].sort((a, b) => Number(a.price) - Number(b.price))

    const askPoints: { price: number; volume: number }[] = []
    let askCumVol = 0
    for (const a of sortedAsksAsc) {
      askCumVol += Number(a.quantity)
      askPoints.push({ price: Number(a.price), volume: askCumVol })
    }

    const maxVol = Math.max(bidCumVol, askCumVol)
    
    // 計算最佳買賣價與中價
    // bidPoints is now Ascending: last element is Best Bid (Highest Price)
    const bestBid = bidPoints[bidPoints.length - 1]?.price || 0
    // askPoints is Ascending: first element is Best Ask (Lowest Price)
    const bestAsk = askPoints[0]?.price || 0
    
    const spread = bestAsk - bestBid
    const midPrice = (bestBid + bestAsk) / 2
    
    // 使用對稱的價格範圍來顯示深度圖
    // bidPoints[0] is now the Lowest Bid Price
    const bidRange = bestBid - (bidPoints[0]?.price || bestBid)
    const askRange = (askPoints[askPoints.length - 1]?.price || bestAsk) - bestAsk
    const maxRange = Math.max(bidRange, askRange) * 1.1 // 留 10% 邊距
    
    const minPrice = Math.max(0, midPrice - maxRange)
    const maxPrice = midPrice + maxRange
    
    return { 
      points: { bids: bidPoints, asks: askPoints }, 
      maxVol, 
      minPrice, 
      maxPrice,
      spread,
      midPrice
    }
  }, [orderbook])

  if (!orderbook || dimensions.width === 0) {
    return <div ref={containerRef} className="w-full h-[400px] flex items-center justify-center text-gray-500">Loading chart...</div>
  }

  const padding = { top: 20, right: 0, bottom: 30, left: 50 }
  const chartWidth = dimensions.width - padding.left - padding.right
  const chartHeight = dimensions.height - padding.top - padding.bottom

  const getX = (price: number) => {
    return ((price - minPrice) / (maxPrice - minPrice)) * chartWidth
  }

  const getY = (volume: number) => {
    return chartHeight - ((volume / maxVol) * chartHeight)
  }

  // Generate SVG paths
  // Bid path: 從最低價的底部開始，畫到最高價，再回到最高價的底部
  const bidPath = `M ${getX(points.bids[0].price)} ${chartHeight} ` + 
    points.bids.map(p => `L ${getX(p.price)} ${getY(p.volume)}`).join(' ') + 
    ` L ${getX(points.bids[points.bids.length - 1].price)} ${chartHeight} Z`
  
  // Ask path: 從最低價的底部開始，畫到最高價，再回到最高價的底部
  const askPath = `M ${getX(points.asks[0].price)} ${chartHeight} ` + 
    points.asks.map(p => `L ${getX(p.price)} ${getY(p.volume)}`).join(' ') + 
    ` L ${getX(points.asks[points.asks.length - 1].price)} ${chartHeight} Z`

  const handleMouseMove = (e: React.MouseEvent) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const x = e.clientX - rect.left - padding.left
    const y = e.clientY - rect.top - padding.top
    
    // Find closest point
    const priceAtX = (x / chartWidth) * (maxPrice - minPrice) + minPrice
    
    // Check bids
    let closestBid = null
    let minBidDist = Infinity
    for (const p of points.bids) {
      const dist = Math.abs(p.price - priceAtX)
      if (dist < minBidDist) {
        minBidDist = dist
        closestBid = p
      }
    }

    // Check asks
    let closestAsk = null
    let minAskDist = Infinity
    for (const p of points.asks) {
      const dist = Math.abs(p.price - priceAtX)
      if (dist < minAskDist) {
        minAskDist = dist
        closestAsk = p
      }
    }

    if (minBidDist < minAskDist && closestBid) {
      setHoverData({
        x: getX(closestBid.price),
        y: getY(closestBid.volume),
        price: closestBid.price,
        volume: closestBid.volume,
        type: 'bid'
      })
    } else if (closestAsk) {
      setHoverData({
        x: getX(closestAsk.price),
        y: getY(closestAsk.volume),
        price: closestAsk.price,
        volume: closestAsk.volume,
        type: 'ask'
      })
    }
  }

  return (
    <div ref={containerRef} className="w-full h-[400px] relative select-none">
      <svg 
        width={dimensions.width} 
        height={dimensions.height} 
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHoverData(null)}
      >
        <g transform={`translate(${padding.left},${padding.top})`}>
          {/* Grid Lines */}
          <line x1="0" y1={chartHeight} x2={chartWidth} y2={chartHeight} stroke="#374151" />
          <line x1="0" y1="0" x2="0" y2={chartHeight} stroke="#374151" />
          
          {/* Spread Area Highlight */}
          {spread > 0 && (
            <rect
              x={getX(midPrice - spread / 2)}
              y="0"
              width={getX(midPrice + spread / 2) - getX(midPrice - spread / 2)}
              height={chartHeight}
              fill="rgba(100, 116, 139, 0.1)"
              stroke="#64748b"
              strokeWidth="1"
              strokeDasharray="4"
            />
          )}
          
          {/* Areas */}
          <path d={bidPath} fill="rgba(34, 197, 94, 0.2)" stroke="#22c55e" strokeWidth="2" />
          <path d={askPath} fill="rgba(239, 68, 68, 0.2)" stroke="#ef4444" strokeWidth="2" />
          
          {/* Mid Price Line */}
          {midPrice > 0 && (
            <>
              <line 
                x1={getX(midPrice)} y1="0" 
                x2={getX(midPrice)} y2={chartHeight} 
                stroke="#fbbf24" 
                strokeWidth="2" 
                strokeDasharray="6 3"
              />
              <text 
                x={getX(midPrice)} 
                y="-5" 
                fill="#fbbf24" 
                fontSize="12" 
                fontWeight="bold"
                textAnchor="middle"
              >
                Mid: ${midPrice.toFixed(2)}
              </text>
            </>
          )}

          {/* Hover Indicator */}
          {hoverData && (
            <>
              <line 
                x1={hoverData.x} y1="0" x2={hoverData.x} y2={chartHeight} 
                stroke="#6b7280" strokeDasharray="4" 
              />
              <circle cx={hoverData.x} cy={hoverData.y} r="4" fill="white" />
            </>
          )}

          {/* X Axis Labels */}
          <text x="0" y={chartHeight + 20} fill="#9ca3af" fontSize="12">${minPrice.toFixed(0)}</text>
          <text x={chartWidth} y={chartHeight + 20} fill="#9ca3af" fontSize="12" textAnchor="end">${maxPrice.toFixed(0)}</text>
          
          {/* Y Axis Labels */}
          <text x="-10" y={chartHeight} fill="#9ca3af" fontSize="12" textAnchor="end">0</text>
          <text x="-10" y="10" fill="#9ca3af" fontSize="12" textAnchor="end">{maxVol.toFixed(2)}</text>
        </g>
      </svg>

      {/* Tooltip */}
      {hoverData && (
        <div 
          className="absolute bg-gray-900 border border-gray-700 p-2 rounded shadow-lg text-xs pointer-events-none"
          style={{ 
            left: hoverData.x + padding.left + 10, 
            top: hoverData.y + padding.top - 40 
          }}
        >
          <div className="font-mono text-white">${hoverData.price.toFixed(2)}</div>
          <div className={`font-mono ${hoverData.type === 'bid' ? 'text-green-500' : 'text-red-500'}`}>
            Vol: {hoverData.volume.toFixed(4)}
          </div>
        </div>
      )}
    </div>
  )
}
