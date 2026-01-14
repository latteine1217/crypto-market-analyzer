'use client'

import { useMemo, useState, useRef, useEffect } from 'react'
import type { RichListStat } from '@/types/market'

interface Props {
  data: RichListStat[]
}

export function RichListChart({ data }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [dimensions, setDimensions] = useState({ width: 0, height: 400 })
  const [hoverIndex, setHoverIndex] = useState<number | null>(null)

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

  const { bars, maxTotal, groups, dates } = useMemo(() => {
    if (!data || data.length === 0) return { bars: [], maxTotal: 0, groups: [], dates: [] }

    const groupedByDate: Record<string, Record<string, number>> = {}
    const allGroups = new Set<string>()

    data.forEach(d => {
      const dateKey = d.snapshot_date
      if (!groupedByDate[dateKey]) {
        groupedByDate[dateKey] = {}
      }
      groupedByDate[dateKey][d.rank_group] = Number(d.total_balance)
      allGroups.add(d.rank_group)
    })

    const getGroupWeight = (group: string) => {
      const clean = group.replace(/,/g, '')
      const match = clean.match(/\[([\d.]+)/)
      if (match) return parseFloat(match[1])
      return 0
    }

    const sortedGroups = Array.from(allGroups).sort((a, b) => getGroupWeight(a) - getGroupWeight(b))
    const sortedDates = Object.keys(groupedByDate).sort()

    let maxTotal = 0
    const bars = sortedDates.map(date => {
      let currentHeight = 0
      const stack = sortedGroups.map(group => {
        const value = groupedByDate[date][group] || 0
        const start = currentHeight
        currentHeight += value
        return { group, value, start, end: currentHeight }
      })
      if (currentHeight > maxTotal) maxTotal = currentHeight
      return { date, stack, total: currentHeight }
    })

    return { bars, maxTotal, groups: sortedGroups, dates: sortedDates }
  }, [data])

  if (!data || data.length === 0 || dimensions.width === 0) {
    return <div ref={containerRef} className="w-full h-[400px] flex items-center justify-center text-gray-500">Loading chart...</div>
  }

  const padding = { top: 20, right: 20, bottom: 40, left: 60 }
  const chartWidth = dimensions.width - padding.left - padding.right
  const chartHeight = dimensions.height - padding.top - padding.bottom
  
  const barWidth = Math.min(40, (chartWidth / bars.length) * 0.6)
  const gap = (chartWidth - (barWidth * bars.length)) / (bars.length + 1)

  // Colors
  const colors = [
    '#93c5fd', '#60a5fa', '#3b82f6',
    '#34d399', '#10b981',
    '#facc15', '#eab308',
    '#fb923c', '#f97316',
    '#f87171', '#ef4444',
    '#a78bfa', '#8b5cf6'
  ]

  const getY = (val: number) => chartHeight - ((val / maxTotal) * chartHeight)

  return (
    <div ref={containerRef} className="w-full h-[400px] relative select-none">
      <svg width={dimensions.width} height={dimensions.height}>
        <g transform={`translate(${padding.left},${padding.top})`}>
          {/* Grid Lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((p, i) => {
            const y = chartHeight * (1 - p)
            return (
              <g key={i}>
                <line x1="0" y1={y} x2={chartWidth} y2={y} stroke="#374151" strokeDasharray="3 3" />
                <text x="-10" y={y + 4} fill="#9ca3af" fontSize="11" textAnchor="end">
                  {((maxTotal * p) / 1000000).toFixed(1)}M
                </text>
              </g>
            )
          })}

          {/* Bars */}
          {bars.map((bar, i) => {
            const x = gap + i * (barWidth + gap)
            return (
              <g 
                key={bar.date} 
                onMouseEnter={() => setHoverIndex(i)}
                onMouseLeave={() => setHoverIndex(null)}
              >
                {bar.stack.map((seg, j) => {
                  const y = getY(seg.end)
                  const height = getY(seg.start) - y
                  return (
                    <rect
                      key={seg.group}
                      x={x}
                      y={y}
                      width={barWidth}
                      height={height}
                      fill={colors[j % colors.length]}
                      opacity={hoverIndex === i ? 0.8 : 1}
                    />
                  )
                })}
                {/* Date Label */}
                <text 
                  x={x + barWidth / 2} 
                  y={chartHeight + 20} 
                  fill="#9ca3af" 
                  fontSize="11" 
                  textAnchor="middle"
                >
                  {new Date(bar.date).toLocaleDateString('zh-TW', { month: '2-digit', day: '2-digit' })}
                </text>
              </g>
            )
          })}
        </g>
      </svg>

      {/* Tooltip */}
      {hoverIndex !== null && (
        <div 
          className="absolute bg-gray-900 border border-gray-700 p-3 rounded shadow-lg text-xs z-10 pointer-events-none"
          style={{ 
            left: padding.left + gap + hoverIndex * (barWidth + gap) + barWidth + 10,
            top: 50,
            maxWidth: '200px'
          }}
        >
          <div className="font-bold mb-2 border-b border-gray-700 pb-1">
            {new Date(bars[hoverIndex].date).toLocaleDateString()}
          </div>
          {bars[hoverIndex].stack.slice().reverse().map((seg, j) => {
            // Need to find original index for color
            const originalIndex = groups.indexOf(seg.group)
            return (
              <div key={seg.group} className="flex justify-between items-center gap-4 mb-1">
                <div className="flex items-center gap-2">
                  <div 
                    className="w-3 h-3 rounded-sm" 
                    style={{ backgroundColor: colors[originalIndex % colors.length] }} 
                  />
                  <span className="text-gray-300">{seg.group}</span>
                </div>
                <span className="font-mono text-white">
                  {(seg.value / 1000).toFixed(0)}k
                </span>
              </div>
            )
          })}
          <div className="mt-2 pt-1 border-t border-gray-700 flex justify-between font-bold">
            <span>Total</span>
            <span>{(bars[hoverIndex].total / 1000000).toFixed(2)}M</span>
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="absolute top-0 right-0 p-2 flex flex-wrap gap-2 justify-end w-1/3 pointer-events-none opacity-50 text-[10px]">
        {groups.map((g, i) => (
          <div key={g} className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: colors[i % colors.length] }} />
            <span className="text-gray-400">{g}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
