'use client';

import React, { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query'
import { fetchMarketPrices } from '@/lib/api-client'
import { formatPrice, formatPercent, formatVolume } from '@/lib/utils'
import Link from 'next/link'
import { FearGreedWidget } from '@/components/FearGreedWidget'
import { SignalTimeline } from '@/components/SignalTimeline'
import { WhaleDistributionChart } from '@/components/charts/WhaleDistributionChart'
import FundingRateHeatmap from '@/components/charts/FundingRateHeatmap'
import { OBIChart } from '@/components/charts/OBIChart'
import { WhaleRadar } from '@/components/WhaleRadar'
import { DataQualityStatus } from '@/components/DataQualityStatus'

export default function HomePage() {
  const { data: prices } = useQuery({
    queryKey: ['marketPrices'],
    queryFn: fetchMarketPrices,
    refetchInterval: 5000,
  })

  // Data is now pre-filtered and includes funding rates from the backend
  const pulseMarkets = prices || [];
  const volumeLeaders = useMemo(() => {
    if (pulseMarkets.length === 0) return [];
    return [...pulseMarkets].sort((a, b) => b.volume_24h - a.volume_24h).slice(0, 12);
  }, [pulseMarkets]);

  const btcMarket = useMemo(() => {
    return pulseMarkets.find((m) => m.symbol === 'BTCUSDT') || pulseMarkets.find((m) => m.symbol.startsWith('BTC'));
  }, [pulseMarkets]);

  const ethMarket = useMemo(() => {
    return pulseMarkets.find((m) => m.symbol === 'ETHUSDT') || pulseMarkets.find((m) => m.symbol.startsWith('ETH'));
  }, [pulseMarkets]);

  const marketBreadth = useMemo(() => {
    if (pulseMarkets.length === 0) return { advancers: 0, decliners: 0, pct: 0 };
    const advancers = pulseMarkets.filter((m) => m.change_24h > 0).length;
    const decliners = pulseMarkets.filter((m) => m.change_24h < 0).length;
    const pct = Math.round((advancers / pulseMarkets.length) * 100);
    return { advancers, decliners, pct };
  }, [pulseMarkets]);

  const topGainer = useMemo(() => {
    if (pulseMarkets.length === 0) return null;
    return pulseMarkets.reduce((best, current) => (current.change_24h > best.change_24h ? current : best));
  }, [pulseMarkets]);

  return (
    <div className="max-w-[1600px] mx-auto space-y-6 animate-in fade-in duration-700">
      {/* Header Section */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-[#1e2329]/50 p-6 rounded-2xl border border-gray-800/50 backdrop-blur-sm">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-3xl font-black tracking-tighter text-white">COMMAND CENTER</h1>
            <Link href="/status" className="flex items-center gap-1.5 bg-green-500/10 px-2 py-0.5 rounded border border-green-500/20 hover:bg-green-500/20 transition-all cursor-pointer">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>
              <span className="text-[10px] font-bold text-green-500 uppercase tracking-widest">System Healthy</span>
            </Link>
          </div>
          <p className="text-sm text-gray-500 font-medium italic">"Fortune favors the prepared mind." — Tactical Market Overview</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/technical" className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold rounded-lg transition-all shadow-lg shadow-blue-900/20 flex items-center gap-2">
            <span>📈</span> TACTICAL CHARTS
          </Link>
          <Link href="/etf" className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-lg transition-all shadow-lg shadow-emerald-900/20 flex items-center gap-2">
            <span>🏦</span> ETF FLOWS
          </Link>
          <Link href="/liquidity" className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs font-bold rounded-lg transition-all border border-gray-700 flex items-center gap-2">
            <span>💧</span> LIQUIDITY RADAR
          </Link>
          <Link href="/onchain" className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs font-bold rounded-lg transition-all border border-gray-700 flex items-center gap-2">
            <span>🐋</span> WHALE TRACKER
          </Link>
        </div>
      </div>

      {/* Top Pulse Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-4">
        <FearGreedWidget />

        <div className="card p-5 flex flex-col justify-center border-blue-500/20 bg-blue-500/5">
          <span className="text-[10px] font-black text-blue-400 uppercase tracking-widest mb-1">BTC PULSE</span>
          <span className="text-2xl font-black text-white">
            {btcMarket ? `$${formatPrice(btcMarket.price)}` : '--'}
          </span>
          <div className="mt-2 flex items-center justify-between text-[11px] font-bold">
            <span className={btcMarket && btcMarket.change_24h >= 0 ? 'text-green-500' : 'text-red-500'}>
              {btcMarket ? formatPercent(btcMarket.change_24h) : '--'}
            </span>
            <span className="text-gray-500">
              FR: {btcMarket?.funding_rate !== undefined ? `${(Number(btcMarket.funding_rate) * 100).toFixed(4)}%` : '--'}
            </span>
          </div>
        </div>

        <div className="card p-5 flex flex-col justify-center border-indigo-500/20 bg-indigo-500/5">
          <span className="text-[10px] font-black text-indigo-400 uppercase tracking-widest mb-1">ETH PULSE</span>
          <span className="text-2xl font-black text-white">
            {ethMarket ? `$${formatPrice(ethMarket.price)}` : '--'}
          </span>
          <div className="mt-2 flex items-center justify-between text-[11px] font-bold">
            <span className={ethMarket && ethMarket.change_24h >= 0 ? 'text-green-500' : 'text-red-500'}>
              {ethMarket ? formatPercent(ethMarket.change_24h) : '--'}
            </span>
            <span className="text-gray-500">
              FR: {ethMarket?.funding_rate !== undefined ? `${(Number(ethMarket.funding_rate) * 100).toFixed(4)}%` : '--'}
            </span>
          </div>
        </div>

        <div className="card p-5 flex flex-col justify-center border-emerald-500/20 bg-emerald-500/5">
          <span className="text-[10px] font-black text-emerald-400 uppercase tracking-widest mb-1">MARKET BREADTH</span>
          <span className="text-2xl font-black text-white">
            {marketBreadth.pct}%
          </span>
          <div className="mt-2 flex items-center justify-between text-[11px] font-bold text-gray-500">
            <span>Adv: {marketBreadth.advancers}</span>
            <span>Dec: {marketBreadth.decliners}</span>
          </div>
        </div>

        <div className="card p-5 flex flex-col justify-center border-amber-500/20 bg-amber-500/5">
          <span className="text-[10px] font-black text-amber-400 uppercase tracking-widest mb-1">TOP GAINER (24H)</span>
          <span className="text-2xl font-black text-white">
            {topGainer ? topGainer.symbol : '--'}
          </span>
          <div className="mt-2 flex items-center justify-between text-[11px] font-bold">
            <span className="text-green-500">
              {topGainer ? formatPercent(topGainer.change_24h) : '--'}
            </span>
            <span className="text-gray-500">
              Vol: {topGainer ? formatVolume(topGainer.volume_24h) : '--'}
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Left: Market Pulse & Signals */}
        <div className="xl:col-span-2 space-y-6">
          <div className="card overflow-hidden border-gray-800/50">
            <div className="p-4 border-b border-gray-800 flex justify-between items-center bg-gray-900/20">
              <h2 className="text-xs font-bold flex items-center gap-2">
                <span className="w-1.5 h-3 bg-green-500 rounded-full"></span>
                LIVE MARKET PULSE
              </h2>
              <div className="flex gap-4 text-[10px] font-mono text-gray-500">
                <span>UNIVERSE: TOP 12</span>
                <span>DATA: BYBIT V5</span>
              </div>
            </div>
            
            <div className="overflow-x-auto custom-scrollbar">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="text-gray-500 text-[10px] uppercase tracking-widest border-b border-gray-800/50">
                    <th className="py-3 px-6 font-bold">Asset</th>
                    <th className="py-3 px-4 text-right font-bold">Price</th>
                    <th className="py-3 px-4 text-right font-bold">24H Change</th>
                    <th className="py-3 px-4 text-right font-bold">Funding</th>
                    <th className="py-3 px-6 text-right font-bold">24H Volume</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/30">
                  {volumeLeaders.map((market) => {
                    const fundingRate = market.funding_rate;
                    
                    return (
                      <tr key={market.symbol} className="hover:bg-blue-500/5 transition-colors group">
                        <td className="py-3 px-6">
                          <div className="flex items-center gap-3">
                            <div className="font-mono font-black text-sm text-gray-200">{market.symbol}</div>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div className="font-mono font-bold text-sm text-gray-100">${formatPrice(market.price)}</div>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div className={`text-sm font-black ${market.change_24h >= 0 ? 'text-[#00c073]' : 'text-[#f6465d]'}`}>
                            {formatPercent(market.change_24h)}
                          </div>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div className={`text-xs font-mono font-medium ${fundingRate !== undefined && fundingRate < 0 ? 'text-green-400' : 'text-gray-400'}`}>
                            {fundingRate !== undefined ? `${(Number(fundingRate) * 100).toFixed(4)}%` : '--'}
                          </div>
                        </td>
                        <td className="py-3 px-6 text-right">
                          <div className="text-xs font-mono text-gray-300">{formatVolume(market.volume_24h)}</div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-6">
            <FundingRateHeatmap />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <OBIChart exchange="bybit" symbol="BTCUSDT" />
            <div className="card h-[400px]">
              <WhaleDistributionChart symbol="BTC" />
            </div>
          </div>

          <div className="card p-6 flex flex-col justify-between border-emerald-500/20 bg-emerald-500/5">
            <div>
              <div className="text-[10px] font-black text-emerald-400 uppercase tracking-widest mb-2">ETF FLOW HUB</div>
              <h3 className="text-xl font-black text-white mb-2">Dedicated ETF Intelligence</h3>
              <p className="text-sm text-gray-400">
                Full ETF flow analytics, issuer concentration, and cumulative divergences now live in a separate
                workspace built for decision-grade macro signals.
              </p>
            </div>
            <div className="mt-4">
              <Link
                href="/etf"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition-all"
              >
                Open ETF Dashboard
              </Link>
            </div>
          </div>
        </div>

        {/* Right Sidebar: Real-time Intel */}
        <div className="space-y-6">
          <div className="h-[520px]">
            <SignalTimeline limit={25} />
          </div>
          <div className="h-[520px]">
            <WhaleRadar />
          </div>
          <div className="h-[420px]">
            <DataQualityStatus />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="card-header">TACTICAL NOTES</h2>
          <div className="p-4 text-sm text-gray-400 space-y-3 font-medium italic">
            <p>• 使用 Signals + Funding Heatmap 快速定位高風險合約。</p>
            <p>• 右側 Whale Radar 可作為中期資金動向的確認訊號。</p>
          </div>
        </div>
      </div>
    </div>
  )
}
