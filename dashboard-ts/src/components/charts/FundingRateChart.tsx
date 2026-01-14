'use client'

import { useEffect, useRef, useMemo } from 'react'
import { 
  createChart, 
  ColorType, 
  HistogramSeries,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
  type HistogramData
} from 'lightweight-charts'
import type { FundingRate } from '@/types/market'

interface Props {
  data: FundingRate[]
}

export function FundingRateChart({ data }: Props) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)

  const stats = useMemo(() => {
    if (!data || data.length === 0) return { latest: 0, average: 0 }
    const rates = data.map(d => Number(d.funding_rate) * 100)
    const latest = rates[rates.length - 1]
    const average = rates.reduce((a, b) => a + b, 0) / rates.length
    return { latest, average }
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

    const series = chart.addSeries(HistogramSeries, {
      color: '#22c55e',
      priceFormat: { type: 'price', precision: 4, minMove: 0.0001 },
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

    const chartData: HistogramData[] = data.map((d) => {
      const val = Number(d.funding_rate) * 100
      return {
        time: Math.floor(new Date(d.timestamp).getTime() / 1000) as UTCTimestamp,
        value: val,
        color: val >= 0 ? '#22c55e' : '#ef4444',
      }
    })

    series.setData(chartData)

    if (chartRef.current) {
      chartRef.current.timeScale().fitContent()
    }
  }, [data])

  return (
    <div>
      <div className="mb-4 flex items-center gap-6 text-sm">
        <div>
          <span className="text-gray-400">Latest: </span>
          <span className={`font-semibold ${stats.latest >= 0 ? 'text-green-500' : 'text-red-500'}`}>
            {stats.latest.toFixed(4)}%
          </span>
        </div>
        <div>
          <span className="text-gray-400">Average: </span>
          <span className="font-semibold text-blue-500">{stats.average.toFixed(4)}%</span>
        </div>
      </div>
      <div ref={chartContainerRef} className="w-full" />
    </div>
  )
}
