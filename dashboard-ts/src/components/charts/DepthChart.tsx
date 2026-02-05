'use client'

import { useMemo, useRef, useEffect, useState } from 'react'
import type { OrderBookSnapshot } from '@/types/market'

interface Props {
  orderbook: OrderBookSnapshot
}

export function DepthChart({ orderbook }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [dimensions, setDimensions] = useState({ width: 0, height: 450 })
  const [hoverData, setHoverData] = useState<{ x: number, y: number, price: number, volume: number, type: 'bid' | 'ask' } | null>(null)

  useEffect(() => {
    if (!containerRef.current) return
    const resizeObserver = new ResizeObserver((entries) => {
      if (entries[0]) {
        setDimensions({
          width: entries[0].contentRect.width,
          height: entries[0].contentRect.height || 450,
        })
      }
    })
    resizeObserver.observe(containerRef.current)
    return () => resizeObserver.disconnect()
  }, [])

  const { points, maxVol, minPrice, maxPrice, spread, midPrice, bestBid, bestAsk } = useMemo(() => {
    if (!orderbook || !orderbook.bids?.length || !orderbook.asks?.length) {
      return { points: { bids: [], asks: [] }, maxVol: 0, minPrice: 0, maxPrice: 0, spread: 0, midPrice: 0, bestBid: 0, bestAsk: 0 }
    }

    // 1. 處理買盤 (Bids): 由高到低累加
    const sortedBidsDesc = [...orderbook.bids].sort((a, b) => Number(b.price) - Number(a.price))
    const bidsWithVol: { price: number; volume: number }[] = []
    let bidCumVol = 0
    for (const b of sortedBidsDesc) {
      bidCumVol += Number(b.quantity)
      bidsWithVol.push({ price: Number(b.price), volume: bidCumVol })
    }
    // 繪圖需要從低價到高價
    const bidPoints = [...bidsWithVol].reverse()

    // 2. 處理賣盤 (Asks): 由低到高累加
    const sortedAsksAsc = [...orderbook.asks].sort((a, b) => Number(a.price) - Number(b.price))
    const askPoints: { price: number; volume: number }[] = []
    let askCumVol = 0
    for (const a of sortedAsksAsc) {
      askCumVol += Number(a.quantity)
      askPoints.push({ price: Number(a.price), volume: askCumVol })
    }

    const maxVol = Math.max(bidCumVol, askCumVol)
    const bestBid = Number(orderbook.bids[0].price)
    const bestAsk = Number(orderbook.asks[0].price)
    const midPrice = (bestBid + bestAsk) / 2
    const spread = bestAsk - bestBid
    
    // 計算價格範圍：為了視覺平衡，取買賣盤較寬的一邊
    const bidRange = bestBid - Number(bidPoints[0].price)
    const askRange = Number(askPoints[askPoints.length - 1].price) - bestAsk
    const maxRange = Math.max(bidRange, askRange, midPrice * 0.0005) // 至少顯示 0.05% 的範圍
    
    const minPrice = midPrice - maxRange
    const maxPrice = midPrice + maxRange
    
    return { 
      points: { bids: bidPoints, asks: askPoints }, 
      maxVol, 
      minPrice, 
      maxPrice,
      spread,
      midPrice,
      bestBid,
      bestAsk
    }
  }, [orderbook])

  if (!orderbook || dimensions.width === 0 || !points.bids.length) {
    return <div ref={containerRef} className="w-full h-full flex items-center justify-center text-gray-500 font-mono text-xs uppercase tracking-widest">Awaiting Liquidity Data...</div>
  }

  const padding = { top: 40, right: 0, bottom: 40, left: 0 }
  const chartWidth = dimensions.width - padding.left - padding.right
  const chartHeight = dimensions.height - padding.top - padding.bottom

  const getX = (price: number) => {
    return ((price - minPrice) / (maxPrice - minPrice)) * chartWidth
  }

  // 使用平方根縮放 (Square Root Scale) 讓小額深度更明顯
  const getY = (volume: number) => {
    if (maxVol <= 0) return chartHeight
    const scaled = Math.sqrt(volume) / Math.sqrt(maxVol)
    return chartHeight - (scaled * chartHeight)
  }

  // 構造 SVG 路徑
  // 買盤：從左側最低價底部開始 -> 爬升 -> 到達最佳買價 -> 回到最佳買價底部
  const bidPath = points.bids.length > 0 ? [
    `M ${getX(points.bids[0].price)} ${chartHeight}`,
    ...points.bids.map(p => `L ${getX(p.price)} ${getY(p.volume)}`),
    `L ${getX(bestBid)} ${chartHeight}`,
    'Z'
  ].join(' ') : ''
  
  // 賣盤：從最佳賣價底部開始 -> 爬升 -> 到達右側最高價 -> 回到最高價底部
  const askPath = points.asks.length > 0 ? [
    `M ${getX(bestAsk)} ${chartHeight}`,
    ...points.asks.map(p => `L ${getX(p.price)} ${getY(p.volume)}`),
    `L ${getX(points.asks[points.asks.length - 1].price)} ${chartHeight}`,
    'Z'
  ].join(' ') : ''

  const handleMouseMove = (e: React.MouseEvent) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const mouseX = e.clientX - rect.left - padding.left
    
    // 將滑鼠 X 坐標轉換回價格
    const priceAtX = (mouseX / chartWidth) * (maxPrice - minPrice) + minPrice
    
    if (priceAtX <= midPrice) {
      // 在買盤尋找最接近的點
      const closest = points.bids.reduce((prev, curr) => 
        Math.abs(curr.price - priceAtX) < Math.abs(prev.price - priceAtX) ? curr : prev
      )
      setHoverData({ x: getX(closest.price), y: getY(closest.volume), price: closest.price, volume: closest.volume, type: 'bid' })
    } else {
      // 在賣盤尋找最接近的點
      const closest = points.asks.reduce((prev, curr) => 
        Math.abs(curr.price - priceAtX) < Math.abs(prev.price - priceAtX) ? curr : prev
      )
      setHoverData({ x: getX(closest.price), y: getY(closest.volume), price: closest.price, volume: closest.volume, type: 'ask' })
    }
  }

  return (
    <div ref={containerRef} className="w-full h-full relative select-none bg-[#0b0e11]/30">
      <svg 
        width={dimensions.width} 
        height={dimensions.height} 
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHoverData(null)}
        className="overflow-visible"
      >
        <g transform={`translate(${padding.left},${padding.top})`}>
          {/* 中價基線 */}
          <line 
            x1={getX(midPrice)} y1="0" 
            x2={getX(midPrice)} y2={chartHeight} 
            stroke="rgba(255, 255, 255, 0.1)" 
            strokeWidth="1" 
            strokeDasharray="4 4"
          />

          {/* 買賣盤填充區域 */}
          <path d={bidPath} fill="url(#bidGradient)" stroke="#00c073" strokeWidth="1.5" strokeLinejoin="round" />
          <path d={askPath} fill="url(#askGradient)" stroke="#f6465d" strokeWidth="1.5" strokeLinejoin="round" />
          
          {/* 漸層定義 */}
          <defs>
            <linearGradient id="bidGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#00c073" stopOpacity="0.4" />
              <stop offset="100%" stopColor="#00c073" stopOpacity="0.05" />
            </linearGradient>
            <linearGradient id="askGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f6465d" stopOpacity="0.4" />
              <stop offset="100%" stopColor="#f6465d" stopOpacity="0.05" />
            </linearGradient>
          </defs>

          {/* 價格標籤 (底部) */}
          <g transform={`translate(0, ${chartHeight + 20})`}>
            <text x={getX(minPrice)} fill="#5e6673" fontSize="10" fontWeight="600" textAnchor="start">${minPrice.toFixed(1)}</text>
            <text x={getX(midPrice)} fill="#848e9c" fontSize="10" fontWeight="bold" textAnchor="middle">${midPrice.toFixed(2)}</text>
            <text x={getX(maxPrice)} fill="#5e6673" fontSize="10" fontWeight="600" textAnchor="end">${maxPrice.toFixed(1)}</text>
          </g>

          {/* 累計成交量標籤 (頂部) */}
          <text x="5" y="-10" fill="#5e6673" fontSize="10" fontWeight="bold">DEPTH: {maxVol.toFixed(2)} BTC</text>

          {/* 懸停十字線與點 */}
          {hoverData && (
            <g>
              <line 
                x1={hoverData.x} y1="0" x2={hoverData.x} y2={chartHeight} 
                stroke="rgba(255,255,255,0.2)" strokeDasharray="2 2" 
              />
              <circle 
                cx={hoverData.x} cy={hoverData.y} r="4" 
                fill={hoverData.type === 'bid' ? '#00c073' : '#f6465d'} 
                stroke="white" strokeWidth="1"
              />
            </g>
          )}
        </g>
      </svg>

      {/* Tooltip */}
      {hoverData && (
        <div 
          className="absolute bg-[#1e2329] border border-gray-700 p-3 rounded shadow-2xl pointer-events-none z-50 backdrop-blur-sm"
          style={{ 
            left: Math.min(hoverData.x + 15, dimensions.width - 140), 
            top: hoverData.y - 60 
          }}
        >
          <div className="text-[10px] text-gray-500 font-bold uppercase mb-1">Price</div>
          <div className="font-mono text-sm text-white font-bold mb-2">${hoverData.price.toFixed(2)}</div>
          <div className="text-[10px] text-gray-500 font-bold uppercase mb-1">Cumulative Vol</div>
          <div className={`font-mono text-sm font-bold ${hoverData.type === 'bid' ? 'text-[#00c073]' : 'text-[#f6465d]'}`}>
            {hoverData.volume.toFixed(4)} BTC
          </div>
        </div>
      )}
    </div>
  )
}