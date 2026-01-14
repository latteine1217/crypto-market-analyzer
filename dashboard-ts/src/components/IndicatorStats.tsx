'use client'

import type { OHLCVWithIndicators } from '@/types/market'
import { formatPrice, formatPercent } from '@/lib/utils'

interface Props {
  data: OHLCVWithIndicators[]
}

export function IndicatorStats({ data }: Props) {
  if (data.length === 0) return <p className="text-gray-400">No data available</p>

  const latest = data[data.length - 1]
  const rsi = latest.rsi_14
  const rsiStatus = rsi
    ? rsi >= 70
      ? 'Overbought'
      : rsi <= 30
      ? 'Oversold'
      : 'Neutral'
    : '-'

  const macdTrend =
    latest.macd && latest.macd_signal
      ? latest.macd > latest.macd_signal
        ? '🟢 Bullish'
        : '🔴 Bearish'
      : '-'

  const stats = [
    { label: 'Latest Price', value: `$${formatPrice(latest.close)}` },
    {
      label: 'RSI (14)',
      value: rsi ? rsi.toFixed(2) : 'N/A',
      extra: rsiStatus,
    },
    {
      label: 'MACD',
      value: latest.macd ? latest.macd.toFixed(4) : 'N/A',
      extra: macdTrend,
    },
    {
      label: 'MACD Signal',
      value: latest.macd_signal ? latest.macd_signal.toFixed(4) : 'N/A',
    },
    {
      label: 'MA 20',
      value: latest.sma_20 ? `$${formatPrice(latest.sma_20)}` : 'N/A',
      extra: latest.sma_20
        ? formatPercent(((latest.close / latest.sma_20 - 1) * 100))
        : '',
    },
    {
      label: 'MA 60',
      value: latest.sma_60 ? `$${formatPrice(latest.sma_60)}` : 'N/A',
      extra: latest.sma_60
        ? formatPercent(((latest.close / latest.sma_60 - 1) * 100))
        : '',
    },
    {
      label: 'MA 200',
      value: latest.sma_200 ? `$${formatPrice(latest.sma_200)}` : 'N/A',
      extra: latest.sma_200
        ? formatPercent(((latest.close / latest.sma_200 - 1) * 100))
        : '',
    },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {stats.map((stat, idx) => (
        <div
          key={idx}
          className="flex flex-col p-4 bg-gray-800/50 rounded border border-gray-700"
        >
          <span className="text-sm text-gray-400 mb-1">{stat.label}</span>
          <div className="flex items-baseline justify-between">
            <span className="text-lg font-semibold text-blue-400">{stat.value}</span>
            {stat.extra && (
              <span className="text-sm text-gray-300">{stat.extra}</span>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
