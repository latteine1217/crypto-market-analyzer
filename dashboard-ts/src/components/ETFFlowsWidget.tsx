'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ComposedChart, ReferenceLine } from 'recharts';
import { fetchETFSummary, fetchETFProducts, fetchTopIssuers } from '@/lib/api-client';

export function ETFFlowsWidget() {
  const [asset, setAsset] = React.useState<'BTC' | 'ETH'>('BTC');
  const [timeframe, setTimeframe] = React.useState(30);

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['etfSummary', asset, timeframe],
    queryFn: () => fetchETFSummary(asset, timeframe),
    refetchInterval: 600000, // 10 分鐘
  });

  const { data: topIssuers, isLoading: issuersLoading } = useQuery({
    queryKey: ['topIssuers', asset, timeframe],
    queryFn: () => fetchTopIssuers(asset, timeframe),
    refetchInterval: 600000,
  });

  const { data: products, isLoading: productsLoading } = useQuery({
    queryKey: ['etfProducts', asset, timeframe],
    queryFn: () => fetchETFProducts(asset, timeframe),
    refetchInterval: 600000,
  });

  const formatCurrency = (value: number) => {
    if (value === 0) return 'N/A';
    const absValue = Math.abs(value);
    if (absValue >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
    if (absValue >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
    if (absValue >= 1e3) return `$${(value / 1e3).toFixed(2)}K`;
    return `$${value.toFixed(2)}`;
  };

  const totalFlow = summary?.reduce((sum, item) => sum + item.total_net_flow_usd, 0) || 0;
  const latestFlow = summary?.[0]?.total_net_flow_usd || 0;

  const issuerComparison = React.useMemo(() => {
    if (!products || products.length === 0) return [];
    const issuerKeyMap: Record<string, 'grayscale' | 'blackrock'> = {
      Grayscale: 'grayscale',
      BlackRock: 'blackrock',
    };
    const byDate = new Map<string, { date: string; grayscale: number; blackrock: number }>();
    for (const item of products) {
      const issuerKey = issuerKeyMap[item.issuer];
      if (!issuerKey) continue;
      const date = item.date;
      const current = byDate.get(date) || { date, grayscale: 0, blackrock: 0 };
      current[issuerKey] += item.net_flow_usd || 0;
      byDate.set(date, current);
    }
    const sorted = Array.from(byDate.values()).sort(
      (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
    );
    let grayscaleCum = 0;
    let blackrockCum = 0;
    return sorted.map((row) => {
      grayscaleCum += row.grayscale;
      blackrockCum += row.blackrock;
      return {
        ...row,
        grayscale_cum: grayscaleCum,
        blackrock_cum: blackrockCum,
        divergence_cum: grayscaleCum - blackrockCum,
      };
    });
  }, [products]);

  const latestIssuerPoint = issuerComparison.length > 0 ? issuerComparison[issuerComparison.length - 1] : null;

  return (
    <div className="card border-gray-800/50">
      <div className="card-header border-b border-gray-800/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-2xl">💰</span>
            <span>{asset} ETF Flows</span>
          </div>
          
          <div className="flex items-center gap-4">
            {/* Asset Toggle */}
            <div className="flex bg-black/40 p-1 rounded-lg border border-gray-700/50 gap-1">
              <button
                className={`px-3 py-1 text-[10px] font-black rounded transition-all ${
                  asset === 'BTC' ? 'bg-blue-600 text-white shadow-lg' : 'text-gray-500 hover:text-gray-300'
                }`}
                onClick={() => setAsset('BTC')}
              >
                BTC
              </button>
              <button
                className={`px-3 py-1 text-[10px] font-black rounded transition-all ${
                  asset === 'ETH' ? 'bg-blue-600 text-white shadow-lg' : 'text-gray-500 hover:text-gray-300'
                }`}
                onClick={() => setAsset('ETH')}
              >
                ETH
              </button>
            </div>

            {/* Timeframe Toggle */}
            <div className="flex bg-black/40 p-1 rounded-lg border border-gray-700/50 gap-1">
              {[7, 30, 90].map((t) => (
                <button
                  key={t}
                  className={`px-3 py-1 text-[10px] font-black rounded transition-all ${
                    timeframe === t ? 'bg-gray-700 text-white shadow-md' : 'text-gray-500 hover:text-gray-300'
                  }`}
                  onClick={() => setTimeframe(t)}
                >
                  {t}D
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="p-6">
        {/* Summary Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-gray-800/30 rounded-lg p-4 border border-gray-700/50">
            <div className="text-gray-400 text-sm mb-1">Latest Daily Flow</div>
            <div className={`text-2xl font-bold ${latestFlow >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {formatCurrency(latestFlow)}
            </div>
          </div>
          
          <div className="bg-gray-800/30 rounded-lg p-4 border border-gray-700/50">
            <div className="text-gray-400 text-sm mb-1">Total {timeframe}D Flow</div>
            <div className={`text-2xl font-bold ${totalFlow >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {formatCurrency(totalFlow)}
            </div>
          </div>

          <div className="bg-gray-800/30 rounded-lg p-4 border border-gray-700/50">
            <div className="text-gray-400 text-sm mb-1">Active Products</div>
            <div className="text-2xl font-bold text-gray-200">
              {summary?.[0]?.product_count || '-'}
            </div>
          </div>
        </div>

        {summaryLoading ? (
          <div className="h-64 bg-gray-800/30 rounded animate-pulse"></div>
        ) : summary && summary.length > 0 ? (
          <>
            {/* Issuer Divergence Chart */}
            <div className="mb-6">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-400">Grayscale vs BlackRock Divergence (Cumulative)</h3>
                {latestIssuerPoint && (
                  <div className="flex items-center gap-3 text-xs text-gray-500">
                    <span>
                      Grayscale: <span className="text-gray-200 font-semibold">{formatCurrency(latestIssuerPoint.grayscale_cum)}</span>
                    </span>
                    <span>
                      BlackRock: <span className="text-gray-200 font-semibold">{formatCurrency(latestIssuerPoint.blackrock_cum)}</span>
                    </span>
                    <span>
                      Divergence: <span className={`font-semibold ${latestIssuerPoint.divergence_cum >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {formatCurrency(latestIssuerPoint.divergence_cum)}
                      </span>
                    </span>
                  </div>
                )}
              </div>
              {productsLoading ? (
                <div className="h-56 bg-gray-800/30 rounded animate-pulse"></div>
              ) : issuerComparison.length > 0 ? (
                <ResponsiveContainer width="100%" height={220}>
                  <ComposedChart data={issuerComparison}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis
                      dataKey="date"
                      stroke="#9CA3AF"
                      fontSize={12}
                      tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                    />
                    <YAxis
                      stroke="#9CA3AF"
                      fontSize={12}
                      tickFormatter={(value) => formatCurrency(value)}
                    />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                      formatter={(value: number | undefined) => value !== undefined ? formatCurrency(value) : 'N/A'}
                    />
                    <ReferenceLine y={0} stroke="#4B5563" strokeDasharray="4 4" />
                    <Line
                      type="monotone"
                      dataKey="grayscale_cum"
                      stroke="#F59E0B"
                      strokeWidth={2}
                      name="Grayscale (Cum)"
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="blackrock_cum"
                      stroke="#3B82F6"
                      strokeWidth={2}
                      name="BlackRock (Cum)"
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="divergence_cum"
                      stroke="#EC4899"
                      strokeWidth={1.5}
                      strokeDasharray="6 4"
                      name="Divergence"
                      dot={false}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              ) : (
                <div className="text-center text-gray-500 py-6">
                  No issuer-level ETF flow data for Grayscale/BlackRock
                </div>
              )}
            </div>

            {/* Daily Flow Chart */}
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-gray-400 mb-3">Daily Net Flows</h3>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={[...summary].reverse()}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis 
                    dataKey="date" 
                    stroke="#9CA3AF" 
                    fontSize={12}
                    tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  />
                  <YAxis 
                    stroke="#9CA3AF" 
                    fontSize={12}
                    tickFormatter={(value) => formatCurrency(value)}
                  />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                    formatter={(value: number | undefined) => value !== undefined ? formatCurrency(value) : 'N/A'}
                  />
                  <Bar 
                    dataKey="total_net_flow_usd" 
                    fill="#3B82F6"
                    name="Net Flow"
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Cumulative Flow Chart */}
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-gray-400 mb-3">Cumulative Flow</h3>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={[...summary].reverse()}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis 
                    dataKey="date" 
                    stroke="#9CA3AF" 
                    fontSize={12}
                    tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  />
                  <YAxis 
                    stroke="#9CA3AF" 
                    fontSize={12}
                    tickFormatter={(value) => formatCurrency(value)}
                  />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                    formatter={(value: number | undefined) => value !== undefined ? formatCurrency(value) : 'N/A'}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="cumulative_flow_usd" 
                    stroke="#10B981" 
                    strokeWidth={2}
                    name="Cumulative"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </>
        ) : (
          <div className="text-center text-gray-500 py-12">
            No ETF flow data available
          </div>
        )}

        {/* Top Issuers Table */}
        {!issuersLoading && topIssuers && topIssuers.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-gray-400 mb-3">Top Issuers ({timeframe}D)</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-gray-500 border-b border-gray-800">
                  <tr>
                    <th className="text-left py-2">Issuer</th>
                    <th className="text-right py-2">Products</th>
                    <th className="text-right py-2">Total Flow</th>
                    <th className="text-right py-2">Avg Daily</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/50">
                  {topIssuers.map((issuer) => (
                    <tr key={issuer.issuer} className="hover:bg-gray-800/30">
                      <td className="py-2 font-medium">{issuer.issuer}</td>
                      <td className="text-right text-gray-400">{issuer.product_count}</td>
                      <td className={`text-right font-bold ${issuer.total_net_flow_usd >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {formatCurrency(issuer.total_net_flow_usd)}
                      </td>
                      <td className="text-right text-gray-400">
                        {formatCurrency(issuer.avg_daily_flow_usd)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Data Source Note */}
        <div className="mt-6 pt-4 border-t border-gray-800/50">
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <span>ℹ️</span>
            <span>
              Data source:{' '}
              <a 
                href="https://farside.co.uk/" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-primary hover:underline font-semibold"
              >
                Farside Investors
              </a>
              {' '}(community-maintained, updated daily at US market close)
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
