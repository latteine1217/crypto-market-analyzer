'use client'

import { useEffect, useRef } from 'react'
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
  onChartCreate?: (chart: IChartApi) => void
  key?: string 
}

export function OpenInterestChart({ data, onChartCreate, key }: Props) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const oiSeriesRef = useRef<any>(null) // 使用 any 確保 setMarkers 等方法可用

  // 1. 準備統計數據
  const latestData = data && data.length > 0 ? data[data.length - 1] : null;
  const latestOI = latestData ? parseFloat(String(latestData.open_interest)) : 0;
  const price = latestData ? parseFloat(String((latestData as any).price || 0)) : 0;
  const latestOIUSD = (latestData && (latestData as any).open_interest_usd && Number((latestData as any).open_interest_usd) > 0) 
    ? parseFloat(String((latestData as any).open_interest_usd)) 
    : (latestOI * price);

  useEffect(() => {
    if (!chartContainerRef.current) return

    // 2. 初始化圖表 (使用 any 繞過嚴格類型檢查)
    const chartOptions: any = {
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
      rightPriceScale: {
        visible: true,
        borderColor: '#374151',
        autoScale: true,
      },
    };

    const chart = createChart(chartContainerRef.current, chartOptions);

    // 3. 建立序列
    const oiSeries = chart.addSeries(AreaSeries, {
      lineColor: '#a855f7', 
      topColor: 'rgba(168, 85, 247, 0.4)',
      bottomColor: 'rgba(168, 85, 247, 0.0)',
      lineWidth: 2,
      priceFormat: { 
        type: 'price', 
        precision: 0,
        minMove: 1,
      },
      title: 'OI',
    })

    chartRef.current = chart
    oiSeriesRef.current = oiSeries
    if (onChartCreate) onChartCreate(chart)

    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth })
      }
    }

    window.addEventListener('resize', handleResize)
    return () => {
      window.removeEventListener('resize', handleResize)
      if (chartRef.current) {
        // 通知外部實例已銷毀 (如果需要，可傳入 null)
        chartRef.current.remove()
        chartRef.current = null
      }
    }
  }, [key]) 

  useEffect(() => {
    const series = oiSeriesRef.current;
    if (!series || !data || data.length === 0) return

    const chartData: AreaData[] = data
      .filter(d => d.timestamp && d.open_interest != null)
      .map((d) => ({
        time: (Math.floor(new Date(d.timestamp).getTime() / 1000)) as UTCTimestamp,
        value: parseFloat(String(d.open_interest)),
      }))
      .sort((a, b) => (a.time as number) - (b.time as number));

    const uniqueData = chartData.filter((item, index, self) =>
      index === self.findIndex((t) => t.time === item.time)
    );

    if (uniqueData.length > 0) {
      series.setData(uniqueData)
      
      // 💡 移除 fitContent()，讓時間軸由外部同步邏輯控制
      requestAnimationFrame(() => {
        if (chartRef.current) {
          chartRef.current.priceScale('right').applyOptions({
            autoScale: true,
          } as any);
        }
      });
    }
  }, [data])

  return (
    <div className="relative">
      <div className="mb-4 flex items-center gap-6 text-xs font-mono">
        <div className="flex gap-2">
          <span className="text-gray-500">Latest OI (USD):</span>
          <span className="text-purple-400 font-bold">
            {latestOIUSD > 0 ? `$${(latestOIUSD / 1e6).toFixed(2)}M` : 'N/A'}
          </span>
        </div>
        <div className="flex gap-2">
          <span className="text-gray-500">Latest OI (Coin):</span>
          <span className="text-gray-200 font-bold">
            {latestOI > 0 ? latestOI.toLocaleString() : 'N/A'}
          </span>
        </div>
      </div>
      <div ref={chartContainerRef} className="w-full" />
    </div>
  )
}
