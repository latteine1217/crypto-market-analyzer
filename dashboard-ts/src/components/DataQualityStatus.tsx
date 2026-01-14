'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchMarketQuality } from '@/lib/api-client';
import { DataQualityMetrics } from '@/types/market';

const statusColors = {
  excellent: 'text-green-500 bg-green-500/10',
  good: 'text-emerald-400 bg-emerald-400/10',
  acceptable: 'text-yellow-500 bg-yellow-500/10',
  poor: 'text-orange-500 bg-orange-500/10',
  critical: 'text-red-500 bg-red-500/10',
};

export const DataQualityStatus: React.FC = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['market-quality'],
    queryFn: fetchMarketQuality,
    refetchInterval: 60000, // 每分鐘更新一次
  });

  if (isLoading) return <div className="animate-pulse h-40 bg-slate-800/50 rounded-xl"></div>;
  if (error) return <div className="text-red-400 p-4 bg-red-400/10 rounded-xl">Failed to load quality metrics</div>;

  return (
    <div className="bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-800 bg-slate-800/30 flex justify-between items-center">
        <h3 className="font-semibold text-slate-200">Data Integrity (K-Line)</h3>
        <span className="text-xs text-slate-400">Target: Missing Rate ≤ 0.1%</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="text-xs text-slate-400 uppercase bg-slate-800/20">
            <tr>
              <th className="px-4 py-2 font-medium">Market</th>
              <th className="px-4 py-2 font-medium text-center">Score</th>
              <th className="px-4 py-2 font-medium text-right">Missing</th>
              <th className="px-4 py-2 font-medium text-right">Rate</th>
              <th className="px-4 py-2 font-medium text-center">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {data?.map((m: DataQualityMetrics) => (
              <tr key={`${m.exchange}-${m.symbol}`} className="hover:bg-slate-800/30 transition-colors">
                <td className="px-4 py-3">
                  <div className="flex flex-col">
                    <span className="font-medium text-slate-200 uppercase">{m.symbol}</span>
                    <span className="text-xs text-slate-500 capitalize">{m.exchange} · {m.timeframe}</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-center">
                  <span className={`font-mono font-bold ${m.quality_score >= 99 ? 'text-green-400' : m.quality_score >= 95 ? 'text-yellow-400' : 'text-red-400'}`}>
                    {m.quality_score.toFixed(1)}
                  </span>
                </td>
                <td className="px-4 py-3 text-right text-slate-300">
                  {m.missing_count} / {m.expected_count}
                </td>
                <td className="px-4 py-3 text-right">
                  <span className={m.missing_rate <= 0.001 ? 'text-green-400' : 'text-orange-400'}>
                    {(m.missing_rate * 100).toFixed(3)}%
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${statusColors[m.status]}`}>
                    {m.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
