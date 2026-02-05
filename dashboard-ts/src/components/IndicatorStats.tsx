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
    { label: 'Latest Price', value: `$${formatPrice(latest.close)}`, color: 'text-blue-400' },
    {
      label: 'RSI (14)',
      value: rsi ? rsi.toFixed(2) : 'N/A',
      extra: rsiStatus,
      extraColor: rsiStatus === 'Overbought' ? 'text-red-400' : rsiStatus === 'Oversold' ? 'text-green-400' : 'text-gray-400'
    },
    {
      label: 'MACD',
      value: latest.macd ? latest.macd.toFixed(2) : 'N/A',
      extra: macdTrend,
    },
    {
      label: 'MACD Signal',
      value: latest.macd_signal ? latest.macd_signal.toFixed(2) : 'N/A',
    },
    {
      label: 'MA 20',
      value: latest.sma_20 ? `$${formatPrice(latest.sma_20)}` : 'N/A',
      color: 'text-blue-400',
      extra: latest.sma_20
        ? formatPercent(((latest.close / latest.sma_20 - 1) * 100))
        : '',
    },
    {
      label: 'MA 60',
      value: latest.sma_60 ? `$${formatPrice(latest.sma_60)}` : 'N/A',
      color: 'text-orange-400',
      extra: latest.sma_60
        ? formatPercent(((latest.close / latest.sma_60 - 1) * 100))
        : '',
    },
    {
      label: 'MA 200',
      value: latest.sma_200 ? `$${formatPrice(latest.sma_200)}` : 'N/A',
      color: 'text-purple-400',
      extra: latest.sma_200
        ? formatPercent(((latest.close / latest.sma_200 - 1) * 100))
        : '',
    },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
      {stats.map((stat, idx) => (
        <div
          key={idx}
          className="flex flex-col p-3 bg-gray-800/40 rounded border border-gray-700/50 hover:bg-gray-800/60 transition-colors"
        >
          <span className="text-[10px] uppercase tracking-wider text-gray-500 mb-1 font-medium">{stat.label}</span>
          <div className="flex items-baseline justify-between gap-2">
            <span className={`text-base font-bold truncate ${stat.color || 'text-gray-100'}`}>
              {stat.value}
            </span>
            {stat.extra && (
              <span className={`text-xs font-medium whitespace-nowrap ${stat.extraColor || 'text-gray-400'}`}>
                {stat.label.includes('RSI') ? `| ${stat.extra}` : stat.extra}
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
