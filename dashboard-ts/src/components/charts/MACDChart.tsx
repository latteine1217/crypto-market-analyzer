'use client'

import { useEffect, useRef } from 'react'
import { 
  createChart, 
  ColorType, 
  HistogramSeries, 
  LineSeries,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
  type LineData,
  type HistogramData
} from 'lightweight-charts'
import type { OHLCVWithIndicators } from '@/types/market'

interface Props {
  data: OHLCVWithIndicators[]
}

export function MACDChart({ data }: Props) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const macdSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const signalSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const histSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)

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
      height: 200,
      timeScale: {
        borderColor: '#374151',
        timeVisible: true,
      },
    })

    const histSeries = chart.addSeries(HistogramSeries, {
      color: '#3b82f6',
      priceFormat: { type: 'price', precision: 4, minMove: 0.0001 },
    })

    const macdSeries = chart.addSeries(LineSeries, {
      color: '#22c55e',
      lineWidth: 2,
      priceFormat: { type: 'price', precision: 4, minMove: 0.0001 },
    })

    const signalSeries = chart.addSeries(LineSeries, {
      color: '#f59e0b',
      lineWidth: 2,
      priceFormat: { type: 'price', precision: 4, minMove: 0.0001 },
    })

    chartRef.current = chart
    histSeriesRef.current = histSeries
    macdSeriesRef.current = macdSeries
    signalSeriesRef.current = signalSeries

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
      histSeriesRef.current = null
      macdSeriesRef.current = null
      signalSeriesRef.current = null
    }
  }, [])

  useEffect(() => {
    const macdSeries = macdSeriesRef.current;
    const signalSeries = signalSeriesRef.current;
    const histSeries = histSeriesRef.current;

    if (!macdSeries || !signalSeries || !histSeries || !data || data.length === 0) return

    const macdData: LineData[] = []
    const signalData: LineData[] = []
    const histData: HistogramData[] = []

    // 準備資料
    data.forEach((d) => {
      if (d.macd === undefined || d.macd_signal === undefined) return
      
      const time = Math.floor(new Date(d.timestamp).getTime() / 1000) as UTCTimestamp
      
      macdData.push({ time, value: d.macd })
      signalData.push({ time, value: d.macd_signal })
      histData.push({ 
        time, 
        value: d.macd_hist || 0,
        color: (d.macd_hist || 0) >= 0 ? '#22c55e' : '#ef4444' 
      })
    })

    macdSeries.setData(macdData)
    signalSeries.setData(signalData)
    histSeries.setData(histData)

    if (chartRef.current) {
      chartRef.current.timeScale().fitContent()
    }
  }, [data])

  return <div ref={chartContainerRef} className="w-full" />
}