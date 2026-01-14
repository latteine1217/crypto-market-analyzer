'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query'
import { fetchMarketPrices } from '@/lib/api-client'
import { formatPrice, formatPercent, formatVolume } from '@/lib/utils'
import Link from 'next/link'
import { DataQualityStatus } from '@/components/DataQualityStatus'
import { NewsList } from '@/components/NewsList'

export default function HomePage() {
  const { data: prices, isLoading, error } = useQuery({
    queryKey: ['marketPrices'],
    queryFn: fetchMarketPrices,
    refetchInterval: 5000,
  })

  // Group prices by exchange for better organization
  const groupedPrices = prices?.reduce((acc, curr) => {
    if (!acc[curr.exchange]) acc[curr.exchange] = [];
    acc[curr.exchange].push(curr);
    return acc;
  }, {} as Record<string, typeof prices>);

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div>
          <h1 className="text-4xl font-bold mb-2 bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-500">
            Market Dashboard
          </h1>
          <p className="text-gray-400">Multi-exchange real-time analysis and monitoring</p>
        </div>
        <div className="flex gap-3">
          <Link href="/technical" className="btn btn-primary shadow-lg shadow-primary/20">
            📈 Technical Analysis
          </Link>
          <Link href="/liquidity" className="btn btn-secondary border-gray-700 hover:bg-gray-800">
            💧 Liquidity Analysis
          </Link>
        </div>
      </div>

      {/* Market Overview Section with Grouping */}
      <div className="card border-gray-800/50">
        <h2 className="card-header flex justify-between items-center border-b border-gray-800/50">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-success animate-pulse"></span>
            <span>Live Market Overview</span>
          </div>
          <span className="text-[10px] font-mono text-gray-500 bg-gray-800/50 px-2 py-1 rounded">
            REFRESH: 5S
          </span>
        </h2>
        <div className="overflow-x-auto">
          {isLoading ? (
            <div className="p-12 space-y-4">
              <div className="h-4 w-1/4 bg-gray-800 rounded animate-pulse"></div>
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-12 bg-gray-800/30 rounded animate-pulse"></div>
              ))}
            </div>
          ) : error ? (
            <div className="p-12 text-center">
              <div className="text-red-400 mb-2">⚠️ Data Synchronization Failed</div>
              <p className="text-xs text-gray-500">Please check api-server connectivity</p>
            </div>
          ) : (
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-900/30 text-gray-500 text-[10px] uppercase tracking-widest border-b border-gray-800/50">
                  <th className="py-4 px-6 font-medium">Exchange / Asset</th>
                  <th className="py-4 px-4 text-right font-medium">Last Price</th>
                  <th className="py-4 px-4 text-right font-medium">24h Change</th>
                  <th className="py-4 px-4 text-right font-medium">24h Range</th>
                  <th className="py-4 px-6 text-right font-medium">24h Volume</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/30">
                {groupedPrices && Object.entries(groupedPrices).map(([exchange, assets]) => (
                  <React.Fragment key={exchange}>
                    <tr className="bg-gray-800/10">
                      <td colSpan={5} className="py-2 px-6 border-y border-gray-800/50">
                        <span className="text-[10px] font-bold text-primary uppercase tracking-widest">{exchange}</span>
                      </td>
                    </tr>
                    {assets.map((market) => (
                      <tr key={`${exchange}-${market.symbol}`} className="hover:bg-primary/5 transition-colors group">
                        <td className="py-4 px-6">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-gray-800 flex items-center justify-center text-xs font-bold text-gray-400 group-hover:text-primary transition-colors">
                              {market.symbol.charAt(0)}
                            </div>
                            <div>
                              <div className="font-mono font-bold text-sm text-gray-200">{market.symbol}</div>
                              <div className="text-[10px] text-gray-500 uppercase tracking-tighter">Spot Market</div>
                            </div>
                          </div>
                        </td>
                        <td className="py-4 px-4 text-right">
                          <div className="font-mono font-bold text-sm text-gray-100">${formatPrice(market.price)}</div>
                        </td>
                        <td className="py-4 px-4 text-right">
                          <div className={`text-sm font-bold flex items-center justify-end gap-1 ${
                            market.change_24h >= 0 ? 'text-success' : 'text-danger'
                          }`}>
                            {market.change_24h >= 0 ? '↑' : '↓'}
                            {formatPercent(market.change_24h)}
                          </div>
                        </td>
                        <td className="py-4 px-4 text-right">
                          <div className="inline-block text-right">
                            <div className="text-[10px] text-gray-400 font-mono">H: ${market.high_24h ? formatPrice(market.high_24h) : '-'}</div>
                            <div className="text-[10px] text-gray-500 font-mono">L: ${market.low_24h ? formatPrice(market.low_24h) : '-'}</div>
                          </div>
                        </td>
                        <td className="py-4 px-6 text-right">
                          <div className="text-xs font-mono text-gray-400">{formatVolume(market.volume_24h)}</div>
                        </td>
                      </tr>
                    ))}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card h-full bg-gradient-to-br from-gray-900 to-black border-gray-800/50">
          <h3 className="card-header border-b border-gray-800/50">Network Status</h3>
          <div className="p-6 grid grid-cols-2 gap-y-8 gap-x-4">
            <div className="space-y-1">
              <div className="text-[10px] uppercase tracking-widest text-gray-500">Ingestion</div>
              <div className="flex items-center gap-2">
                <span className="flex h-2 w-2 relative">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-success"></span>
                </span>
                <span className="text-lg font-bold text-gray-200">Active</span>
              </div>
            </div>
            <div className="space-y-1">
              <div className="text-[10px] uppercase tracking-widest text-gray-500">Exchanges</div>
              <div className="text-lg font-bold text-gray-200">3 Nodes</div>
            </div>
            <div className="space-y-1">
              <div className="text-[10px] uppercase tracking-widest text-gray-500">Live Streams</div>
              <div className="text-lg font-bold text-gray-200">12 Channels</div>
            </div>
            <div className="space-y-1">
              <div className="text-[10px] uppercase tracking-widest text-gray-500">Uptime</div>
              <div className="text-lg font-bold text-success">99.98%</div>
            </div>
          </div>
          
          <div className="m-6 p-4 bg-primary/5 border border-primary/10 rounded-xl relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-2 opacity-10 group-hover:opacity-20 transition-opacity">
              <svg className="w-12 h-12" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2L1 21h22L12 2zm0 3.45l8.27 14.3H3.73L12 5.45zM11 16h2v2h-2v-2zm0-6h2v4h-2v-4z"/>
              </svg>
            </div>
            <h4 className="text-xs font-bold text-primary mb-2 flex items-center gap-2">
              <span className="w-1 h-3 bg-primary rounded-full"></span>
              INFRASTRUCTURE NOTE
            </h4>
            <p className="text-[10px] text-gray-400 leading-relaxed max-w-[90%]">
              Distributed WebSocket collectors are deployed per exchange. 
              Subscribed to BTC/USDT and ETH/USDT streams for microsecond trade precision and full L2 order book depth.
            </p>
          </div>
        </div>

        <DataQualityStatus />
      </div>

      <div className="mt-6">
        <NewsList />
      </div>
    </div>
  )
}