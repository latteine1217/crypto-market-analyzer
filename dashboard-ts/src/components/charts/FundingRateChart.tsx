'use client'

import { useEffect, useRef, useMemo } from 'react'
import { 
  createChart, 
  ColorType, 
  HistogramSeries,
  LineSeries,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
  type HistogramData,
  type LineData
} from 'lightweight-charts'
import type { FundingRate } from '@/types/market'

interface Props {
  data: FundingRate[]
  onChartCreate?: (chart: IChartApi) => void
  key?: string 
}

export function FundingRateChart({ data, onChartCreate, key }: Props) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)
  const predictedSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const isFirstLoadRef = useRef(true) 
  const previousKeyRef = useRef(key)

  if (key !== previousKeyRef.current) {
    isFirstLoadRef.current = true
    previousKeyRef.current = key
  }

  const stats = useMemo(() => {
    if (!data || data.length === 0) return { latest: 0, average: 0, predicted: 0 }
    const rates = data.map(d => Number(d.funding_rate) * 100)
    const latest = rates[rates.length - 1]
    const average = rates.reduce((a, b) => a + b, 0) / rates.length
    const lastData = data[data.length - 1]
    // 取得預測費率 (如果有的話)
    const predicted = (lastData as any).predicted_funding_rate ? Number((lastData as any).predicted_funding_rate) * 100 : latest
    return { latest, average, predicted }
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

    if (onChartCreate) onChartCreate(chart)

    const series = chart.addSeries(HistogramSeries, {
      color: '#22c55e',
      priceFormat: { type: 'price', precision: 4, minMove: 0.0001 },
      title: 'Settled'
    })

    const predictedSeries = chart.addSeries(LineSeries, {
      color: '#3b82f6', // Blue for prediction
      lineWidth: 2,
      lineStyle: 2, // Dashed line
      title: 'Predicted'
    })

    chartRef.current = chart
    seriesRef.current = series
    predictedSeriesRef.current = predictedSeries

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
      predictedSeriesRef.current = null
    }
  }, [])

  useEffect(() => {
    const series = seriesRef.current;
    const predSeries = predictedSeriesRef.current;
    if (!series || !predSeries || !data || data.length === 0) return

    const chartData: HistogramData[] = []
    const predData: LineData[] = []

    data.forEach((d) => {
      const time = Math.floor(new Date(d.timestamp).getTime() / 1000) as UTCTimestamp
      const val = Number(d.funding_rate) * 100
      
      chartData.push({
        time,
        value: val,
        color: val >= 0 ? 'rgba(34, 197, 94, 0.7)' : 'rgba(239, 68, 68, 0.7)',
      })

      // 預測費率連線
      const predVal = (d as any).predicted_funding_rate ? Number((d as any).predicted_funding_rate) * 100 : val
      predData.push({
        time,
        value: predVal
      })
    })

    series.setData(chartData)
    predSeries.setData(predData)

    // ✅ 僅在首次載入時自動調整範圍，顯示最新 120 筆資料
    if (isFirstLoadRef.current && chartRef.current && chartData.length > 0) {
      const barCount = Math.min(120, chartData.length)
      const from = Math.max(0, chartData.length - barCount)
      chartRef.current.timeScale().setVisibleLogicalRange({
        from: from,
        to: chartData.length - 1
      })
      isFirstLoadRef.current = false
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
