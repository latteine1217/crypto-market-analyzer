'use client'

import { useEffect, useRef, useMemo } from 'react'
import { 
  createChart, 
  ColorType, 
  AreaSeries,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
  type AreaData
} from 'lightweight-charts'
import type { OpenInterest } from '@/types/market'

interface Props {
  data: OpenInterest[]
}

export function OpenInterestChart({ data }: Props) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Area'> | null>(null)

  const stats = useMemo(() => {
    if (!data || data.length === 0) return { latestUsd: 0, latestCoin: 0, change: 0 }
    const first = data[0].open_interest_usd || 0
    const last = data[data.length - 1].open_interest_usd || 0
    const change = first ? ((last - first) / first * 100) : 0
    return {
      latestUsd: last / 1000000,
      latestCoin: Number(data[data.length - 1].open_interest),
      change
    }
  }, [data])

  useEffect(() => {
    if (!chartContainerRef.current) return

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
      height: 250,
      timeScale: {
        borderColor: '#374151',
        timeVisible: true,
      },
    })

    const series = chart.addSeries(AreaSeries, {
      lineColor: '#8b5cf6',
      topColor: 'rgba(139, 92, 246, 0.3)',
      bottomColor: 'rgba(139, 92, 246, 0)',
      lineWidth: 2,
    })

    chartRef.current = chart
    seriesRef.current = series

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
      }
      seriesRef.current = null
    }
  }, [])

  useEffect(() => {
    const series = seriesRef.current;
    if (!series || !data || data.length === 0) return

    const chartData: AreaData[] = data.map((d) => ({
      time: Math.floor(new Date(d.timestamp).getTime() / 1000) as UTCTimestamp,
      value: (d.open_interest_usd || 0) / 1000000,
    }))

    series.setData(chartData)

    if (chartRef.current) {
      chartRef.current.timeScale().fitContent()
    }
  }, [data])

  return (
    <div>
      <div className="mb-4 flex items-center gap-6 text-sm">
        <div>
          <span className="text-gray-400">Latest OI (USD): </span>
          <span className="font-semibold text-purple-400">${stats.latestUsd.toFixed(2)}M</span>
        </div>
        <div>
          <span className="text-gray-400">Latest OI (Coin): </span>
          <span className="font-semibold text-gray-300">{stats.latestCoin.toFixed(2)}</span>
        </div>
        <div>
          <span className="text-gray-400">Trend: </span>
          <span className={`font-semibold ${stats.change >= 0 ? 'text-green-500' : 'text-red-500'}`}>
            {stats.change > 0 ? '+' : ''}{stats.change.toFixed(2)}%
          </span>
        </div>
      </div>
      <div ref={chartContainerRef} className="w-full" />
    </div>
  )
}
