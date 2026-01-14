'use client'

import { useQuery } from '@tanstack/react-query'
import { fetchMarketPrices } from '@/lib/api-client'
import { formatPrice, formatPercent, formatVolume } from '@/lib/utils'

export default function OverviewPage() {
  const { data: prices, isLoading, error } = useQuery({
    queryKey: ['marketPrices'],
    queryFn: fetchMarketPrices,
    refetchInterval: 5000, // Refetch every 5 seconds
  })

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-20 w-64 bg-gray-800 rounded-lg"></div>
        <div className="card">
          <div className="h-10 bg-gray-800 border-b border-gray-700"></div>
          <div className="space-y-2 p-4">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="h-12 bg-gray-800/50 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return <div className="text-red-500">Error loading market data</div>
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">Market Overview</h1>
        <p className="text-gray-400">Real-time prices across all markets</p>
      </div>

      <div className="card">
        <h2 className="card-header">All Markets</h2>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="text-left py-3 px-4">Exchange</th>
                <th className="text-left py-3 px-4">Symbol</th>
                <th className="text-right py-3 px-4">Price</th>
                <th className="text-right py-3 px-4">24h Change</th>
                <th className="text-right py-3 px-4">24h High</th>
                <th className="text-right py-3 px-4">24h Low</th>
                <th className="text-right py-3 px-4">24h Volume</th>
              </tr>
            </thead>
            <tbody>
              {prices?.map((market, idx) => (
                <tr
                  key={`${market.exchange}-${market.symbol}`}
                  className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors"
                >
                  <td className="py-3 px-4">
                    <span className="font-medium">{market.exchange}</span>
                  </td>
                  <td className="py-3 px-4">
                    <span className="font-mono font-semibold">{market.symbol}</span>
                  </td>
                  <td className="text-right py-3 px-4 font-mono">
                    ${formatPrice(market.price)}
                  </td>
                  <td className="text-right py-3 px-4">
                    <span
                      className={
                        market.change_24h >= 0 ? 'text-success' : 'text-danger'
                      }
                    >
                      {formatPercent(market.change_24h)}
                    </span>
                  </td>
                  <td className="text-right py-3 px-4 font-mono text-sm text-gray-400">
                    {market.high_24h ? `$${formatPrice(market.high_24h)}` : '-'}
                  </td>
                  <td className="text-right py-3 px-4 font-mono text-sm text-gray-400">
                    {market.low_24h ? `$${formatPrice(market.low_24h)}` : '-'}
                  </td>
                  <td className="text-right py-3 px-4 text-sm text-gray-400">
                    {market.volume_24h ? formatVolume(market.volume_24h) : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
