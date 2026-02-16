'use client';

import React from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ComposedChart,
  ReferenceLine,
} from 'recharts';
import { fetchETFAnalytics, fetchETFProducts, fetchTopIssuers } from '@/lib/api-client';
import { QUERY_PROFILES } from '@/lib/queryProfiles';

type FlowStreak = {
  count: number;
  direction: 'inflow' | 'outflow' | 'neutral';
};

export default function EtfPage() {
  const [asset, setAsset] = React.useState<'BTC' | 'ETH'>('BTC');
  const [timeframe, setTimeframe] = React.useState(30);
  const [compareProduct, setCompareProduct] = React.useState<'IBIT' | 'FBTC' | 'GBTC'>('IBIT');

  const { data: analytics, isLoading: analyticsLoading } = useQuery({
    queryKey: ['etfAnalytics', asset, timeframe],
    queryFn: () => fetchETFAnalytics(asset, timeframe),
    ...QUERY_PROFILES.tenMinutes,
  });

  const { data: products, isLoading: productsLoading } = useQuery({
    queryKey: ['etfProducts', asset, timeframe],
    queryFn: () => fetchETFProducts(asset, timeframe),
    ...QUERY_PROFILES.tenMinutes,
  });

  const { data: topIssuers, isLoading: issuersLoading } = useQuery({
    queryKey: ['topIssuers', asset, timeframe],
    queryFn: () => fetchTopIssuers(asset, timeframe),
    ...QUERY_PROFILES.tenMinutes,
  });

  const formatCurrency = (value: number) => {
    if (value === 0) return 'N/A';
    const absValue = Math.abs(value);
    if (absValue >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
    if (absValue >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
    if (absValue >= 1e3) return `$${(value / 1e3).toFixed(2)}K`;
    return `$${value.toFixed(2)}`;
  };

  const formatPct = (value: number | null | undefined) => {
    if (value === null || value === undefined) return 'N/A';
    return `${(value * 100).toFixed(2)}%`;
  };

  const formatMultiple = (value: number | null | undefined) => {
    if (value === null || value === undefined) return 'N/A';
    return `${value.toFixed(2)}x`;
  };

  const formatBtc = (value: number | null | undefined) => {
    if (value === null || value === undefined) return 'N/A';
    return `${value.toFixed(2)} BTC`;
  };

  const summaryRows = analytics?.data || [];
  const summaryRowsDesc = React.useMemo(() => {
    return summaryRows.length > 0 ? [...summaryRows].reverse() : [];
  }, [summaryRows]);
  const latestFlow = summaryRows[0]?.total_net_flow_usd || 0;
  const totalFlow = summaryRows.reduce((sum, item) => sum + item.total_net_flow_usd, 0);
  const avgFlow = summaryRows.length > 0 ? totalFlow / summaryRows.length : 0;
  const productCount = summaryRows[0]?.product_count || 0;
  const latestRow = summaryRows[0];

  const flowStreak = React.useMemo<FlowStreak>(() => {
    if (!summaryRows.length) return { count: 0, direction: 'neutral' };
    const sign = latestFlow > 0 ? 1 : latestFlow < 0 ? -1 : 0;
    if (sign === 0) return { count: 0, direction: 'neutral' };
    let count = 0;
    for (const item of summaryRows) {
      const s = item.total_net_flow_usd > 0 ? 1 : item.total_net_flow_usd < 0 ? -1 : 0;
      if (s !== sign) break;
      count += 1;
    }
    return { count, direction: sign > 0 ? 'inflow' : 'outflow' };
  }, [summaryRows, latestFlow]);

  const { largestInflow, largestOutflow } = React.useMemo(() => {
    if (!summaryRows.length) return { largestInflow: null, largestOutflow: null };
    let max = summaryRows[0];
    let min = summaryRows[0];
    for (const item of summaryRows) {
      if (item.total_net_flow_usd > max.total_net_flow_usd) max = item;
      if (item.total_net_flow_usd < min.total_net_flow_usd) min = item;
    }
    return { largestInflow: max, largestOutflow: min };
  }, [summaryRows]);

  const dominantIssuer = topIssuers && topIssuers.length > 0 ? topIssuers[0] : null;

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

  const productComparison = React.useMemo(() => {
    if (!products || products.length === 0) return [];
    const baseline = compareProduct === 'GBTC' ? 'IBIT' : 'GBTC';
    const byDate = new Map<string, { date: string; primary: number; baseline: number }>();
    for (const item of products) {
      if (item.product_code !== compareProduct && item.product_code !== baseline) continue;
      const date = item.date;
      const current = byDate.get(date) || { date, primary: 0, baseline: 0 };
      if (item.product_code === compareProduct) current.primary += item.net_flow_usd || 0;
      if (item.product_code === baseline) current.baseline += item.net_flow_usd || 0;
      byDate.set(date, current);
    }
    const sorted = Array.from(byDate.values()).sort(
      (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
    );
    let primaryCum = 0;
    let baselineCum = 0;
    return sorted.map((row) => {
      primaryCum += row.primary;
      baselineCum += row.baseline;
      return {
        ...row,
        primary_cum: primaryCum,
        baseline_cum: baselineCum,
        divergence_cum: primaryCum - baselineCum,
        baseline,
      };
    });
  }, [products, compareProduct]);

  const productLeaders = React.useMemo(() => {
    if (!products || products.length === 0) return [];
    const map = new Map<string, { product_code: string; issuer: string; total_flow: number }>();
    for (const item of products) {
      const entry = map.get(item.product_code) || {
        product_code: item.product_code,
        issuer: item.issuer,
        total_flow: 0,
      };
      entry.total_flow += item.net_flow_usd || 0;
      map.set(item.product_code, entry);
    }
    return Array.from(map.values())
      .sort((a, b) => b.total_flow - a.total_flow)
      .slice(0, 6);
  }, [products]);

  const latestIssuerPoint = issuerComparison.length > 0 ? issuerComparison[issuerComparison.length - 1] : null;
  const latestProductPoint = productComparison.length > 0 ? productComparison[productComparison.length - 1] : null;
  const signalRows = React.useMemo(() => {
    return summaryRows
      .filter((row) => row.flow_shock || row.price_divergence)
      .slice(0, 10);
  }, [summaryRows]);

  return (
    <div className="max-w-[1600px] mx-auto space-y-6 animate-in fade-in duration-700">
      <div className="card border-emerald-500/20 bg-emerald-500/5">
        <div className="p-6 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <span className="text-2xl">🏦</span>
              <h1 className="text-2xl md:text-3xl font-black tracking-tight text-white">
                ETF Flow Intelligence
              </h1>
            </div>
            <p className="text-sm text-gray-400 max-w-2xl">
              Daily ETF flow monitoring with issuer concentration, cumulative divergence, and regime shifts aligned to
              US market close (16:00 ET).
            </p>
            <div className="mt-3 text-[11px] text-gray-500">
              Data source:{' '}
              <Link
                href="https://sosovalue.xyz/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-emerald-300 hover:underline font-semibold"
              >
                SoSoValue
              </Link>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <div className="flex bg-black/40 p-1 rounded-lg border border-gray-700/50 gap-1">
              <button
                className={`px-4 py-2 text-[11px] font-black rounded transition-all ${
                  asset === 'BTC' ? 'bg-emerald-600 text-white shadow-lg' : 'text-gray-500 hover:text-gray-300'
                }`}
                onClick={() => setAsset('BTC')}
              >
                BTC
              </button>
              <button
                className={`px-4 py-2 text-[11px] font-black rounded transition-all ${
                  asset === 'ETH' ? 'bg-emerald-600 text-white shadow-lg' : 'text-gray-500 hover:text-gray-300'
                }`}
                onClick={() => setAsset('ETH')}
              >
                ETH
              </button>
            </div>
            <div className="flex bg-black/40 p-1 rounded-lg border border-gray-700/50 gap-1">
              {[7, 30, 90].map((t) => (
                <button
                  key={t}
                  className={`px-4 py-2 text-[11px] font-black rounded transition-all ${
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

      <div className="grid grid-cols-1 md:grid-cols-3 xl:grid-cols-6 gap-4">
        <div className={`stat-card ${latestFlow >= 0 ? 'glow-green' : 'glow-red'}`}>
          <div className="stat-label">Latest Daily Flow</div>
          <div className={`stat-value ${latestFlow >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {formatCurrency(latestFlow)}
          </div>
        </div>
        <div className={`stat-card ${totalFlow >= 0 ? 'glow-green' : 'glow-red'}`}>
          <div className="stat-label">Total {timeframe}D Flow</div>
          <div className={`stat-value ${totalFlow >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {formatCurrency(totalFlow)}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Avg Daily Flow</div>
          <div className="stat-value text-gray-100">{formatCurrency(avgFlow)}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Flow Streak</div>
          <div className="stat-value text-gray-100">
            {flowStreak.direction === 'neutral'
              ? 'N/A'
              : `${flowStreak.count}D ${flowStreak.direction === 'inflow' ? 'Inflow' : 'Outflow'}`}
          </div>
          {analytics?.meta && (
            <div className="text-xs text-gray-500 mt-1">
              Inflow {analytics.meta.inflow_streak}D · Outflow {analytics.meta.outflow_streak}D
            </div>
          )}
        </div>
        <div className="stat-card">
          <div className="stat-label">Active Products</div>
          <div className="stat-value text-gray-100">{productCount || '-'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Dominant Issuer</div>
          <div className="stat-value text-gray-100">
            {dominantIssuer ? dominantIssuer.issuer : 'N/A'}
          </div>
          {dominantIssuer && (
            <div className="text-xs text-gray-400 mt-1">
              {formatCurrency(dominantIssuer.total_net_flow_usd)}
            </div>
          )}
        </div>
        <div className="stat-card">
          <div className="stat-label">Flow Concentration</div>
          <div className="stat-value text-gray-100">
            {latestRow?.issuer_concentration_top1 !== null && latestRow?.issuer_concentration_top1 !== undefined
              ? `${(latestRow.issuer_concentration_top1 * 100).toFixed(1)}%`
              : 'N/A'}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            Top3 {latestRow?.issuer_concentration_top3 ? `${(latestRow.issuer_concentration_top3 * 100).toFixed(1)}%` : 'N/A'}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 space-y-6">
          <div className="card p-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-400">Flow vs BTC Price</h3>
              <div className="text-[10px] text-gray-500">BTC Close (Spot)</div>
              {latestRow?.price_divergence && (
                <div className="text-xs font-semibold text-amber-400">
                  Divergence: {latestRow.price_divergence.replace('_', ' ')}
                </div>
              )}
            </div>
            {analyticsLoading ? (
              <div className="h-56 bg-gray-800/30 rounded animate-pulse"></div>
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <ComposedChart data={summaryRowsDesc}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis
                    dataKey="date"
                    stroke="#9CA3AF"
                    fontSize={12}
                    tickFormatter={(value) =>
                      new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                    }
                  />
                  <YAxis
                    yAxisId="flow"
                    stroke="#9CA3AF"
                    fontSize={12}
                    tickFormatter={(value) => formatCurrency(value)}
                  />
                  <YAxis
                    yAxisId="price"
                    orientation="right"
                    stroke="#9CA3AF"
                    fontSize={12}
                    tickFormatter={(value) => `$${Number(value).toLocaleString()}`}
                  />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                    formatter={(value, name) => {
                      if (value === undefined || value === null) return 'N/A';
                      const numericValue = typeof value === 'number' ? value : Number(value);
                      if (Number.isNaN(numericValue)) return 'N/A';
                      if (name === 'btc_close') return `$${numericValue.toLocaleString()}`;
                      return formatCurrency(numericValue);
                    }}
                  />
                  <Bar yAxisId="flow" dataKey="total_net_flow_usd" fill="#10B981" name="Net Flow" />
                  <Line
                    yAxisId="price"
                    type="monotone"
                    dataKey="btc_close"
                    stroke="#F59E0B"
                    strokeWidth={2}
                    dot={false}
                    name="BTC Close"
                  />
                </ComposedChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="card p-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-400">Grayscale vs BlackRock Divergence (Cumulative)</h3>
              {latestIssuerPoint && (
                <div className="flex items-center gap-3 text-xs text-gray-500">
                  <span>
                    Grayscale:{' '}
                    <span className="text-gray-200 font-semibold">
                      {formatCurrency(latestIssuerPoint.grayscale_cum)}
                    </span>
                  </span>
                  <span>
                    BlackRock:{' '}
                    <span className="text-gray-200 font-semibold">
                      {formatCurrency(latestIssuerPoint.blackrock_cum)}
                    </span>
                  </span>
                  <span>
                    Divergence:{' '}
                    <span
                      className={`font-semibold ${
                        latestIssuerPoint.divergence_cum >= 0 ? 'text-green-400' : 'text-red-400'
                      }`}
                    >
                      {formatCurrency(latestIssuerPoint.divergence_cum)}
                    </span>
                  </span>
                </div>
              )}
            </div>
            {productsLoading ? (
              <div className="h-56 bg-gray-800/30 rounded animate-pulse"></div>
            ) : issuerComparison.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <ComposedChart data={issuerComparison}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis
                    dataKey="date"
                    stroke="#9CA3AF"
                    fontSize={12}
                    tickFormatter={(value) =>
                      new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                    }
                  />
                  <YAxis stroke="#9CA3AF" fontSize={12} tickFormatter={(value) => formatCurrency(value)} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                    formatter={(value: number | undefined) => (value !== undefined ? formatCurrency(value) : 'N/A')}
                  />
                  <ReferenceLine y={0} stroke="#4B5563" strokeDasharray="4 4" />
                  <Line type="monotone" dataKey="grayscale_cum" stroke="#F59E0B" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="blackrock_cum" stroke="#3B82F6" strokeWidth={2} dot={false} />
                  <Line
                    type="monotone"
                    dataKey="divergence_cum"
                    stroke="#EC4899"
                    strokeWidth={1.5}
                    strokeDasharray="6 4"
                    dot={false}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-center text-gray-500 py-6">No issuer-level ETF flow data available</div>
            )}
          </div>

          <div className="card p-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-400">Issuer Comparison (Cumulative)</h3>
              <div className="flex bg-black/40 p-1 rounded-lg border border-gray-700/50 gap-1">
                {(['IBIT', 'FBTC', 'GBTC'] as const).map((code) => (
                  <button
                    key={code}
                    className={`px-3 py-1 text-[10px] font-black rounded transition-all ${
                      compareProduct === code ? 'bg-emerald-600 text-white shadow-lg' : 'text-gray-500 hover:text-gray-300'
                    }`}
                    onClick={() => setCompareProduct(code)}
                  >
                    {code}
                  </button>
                ))}
              </div>
            </div>
            {productsLoading ? (
              <div className="h-56 bg-gray-800/30 rounded animate-pulse"></div>
            ) : productComparison.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <ComposedChart data={productComparison}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis
                    dataKey="date"
                    stroke="#9CA3AF"
                    fontSize={12}
                    tickFormatter={(value) =>
                      new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                    }
                  />
                  <YAxis stroke="#9CA3AF" fontSize={12} tickFormatter={(value) => formatCurrency(value)} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                    formatter={(value: number | undefined) => (value !== undefined ? formatCurrency(value) : 'N/A')}
                  />
                  <ReferenceLine y={0} stroke="#4B5563" strokeDasharray="4 4" />
                  <Line
                    type="monotone"
                    dataKey="primary_cum"
                    stroke="#22D3EE"
                    strokeWidth={2}
                    dot={false}
                    name={compareProduct}
                  />
                  <Line
                    type="monotone"
                    dataKey="baseline_cum"
                    stroke="#F97316"
                    strokeWidth={2}
                    dot={false}
                    name={latestProductPoint?.baseline || 'GBTC'}
                  />
                  <Line
                    type="monotone"
                    dataKey="divergence_cum"
                    stroke="#EC4899"
                    strokeWidth={1.5}
                    strokeDasharray="6 4"
                    dot={false}
                    name="Divergence"
                  />
                </ComposedChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-center text-gray-500 py-6">No product-level data available</div>
            )}
          </div>

          <div className="card p-6">
            <h3 className="text-sm font-semibold text-gray-400 mb-3">Daily Net Flows</h3>
            {analyticsLoading ? (
              <div className="h-56 bg-gray-800/30 rounded animate-pulse"></div>
            ) : (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={summaryRowsDesc}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis
                    dataKey="date"
                    stroke="#9CA3AF"
                    fontSize={12}
                    tickFormatter={(value) =>
                      new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                    }
                  />
                  <YAxis stroke="#9CA3AF" fontSize={12} tickFormatter={(value) => formatCurrency(value)} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                    formatter={(value: number | undefined) => (value !== undefined ? formatCurrency(value) : 'N/A')}
                  />
                  <Bar dataKey="total_net_flow_usd" fill="#10B981" name="Net Flow" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="card p-6">
            <h3 className="text-sm font-semibold text-gray-400 mb-3">Cumulative Flow</h3>
            {analyticsLoading ? (
              <div className="h-56 bg-gray-800/30 rounded animate-pulse"></div>
            ) : (
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={summaryRowsDesc}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis
                    dataKey="date"
                    stroke="#9CA3AF"
                    fontSize={12}
                    tickFormatter={(value) =>
                      new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                    }
                  />
                  <YAxis stroke="#9CA3AF" fontSize={12} tickFormatter={(value) => formatCurrency(value)} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                    formatter={(value: number | undefined) => (value !== undefined ? formatCurrency(value) : 'N/A')}
                  />
                  <Line type="monotone" dataKey="cumulative_flow_usd" stroke="#22D3EE" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="card p-6">
            <h3 className="text-sm font-semibold text-gray-400 mb-3">Flow Impulse (Z-Score)</h3>
            {analyticsLoading ? (
              <div className="h-56 bg-gray-800/30 rounded animate-pulse"></div>
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={summaryRowsDesc}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis
                    dataKey="date"
                    stroke="#9CA3AF"
                    fontSize={12}
                    tickFormatter={(value) =>
                      new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                    }
                  />
                  <YAxis stroke="#9CA3AF" fontSize={12} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                    formatter={(value: number | undefined) => (value !== undefined ? value.toFixed(2) : 'N/A')}
                  />
                  <Bar dataKey="flow_zscore" name="Z-Score" fill="#6366F1" />
                  <ReferenceLine y={2} stroke="#F59E0B" strokeDasharray="4 4" />
                  <ReferenceLine y={-2} stroke="#F59E0B" strokeDasharray="4 4" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="card p-6">
            <h3 className="text-sm font-semibold text-gray-400 mb-3">Signal Watchlist</h3>
            {analyticsLoading ? (
              <div className="h-40 bg-gray-800/30 rounded animate-pulse"></div>
            ) : signalRows.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-gray-500 border-b border-gray-800">
                    <tr>
                      <th className="text-left py-2">Date</th>
                      <th className="text-right py-2">Net Flow</th>
                      <th className="text-right py-2">Z-Score</th>
                      <th className="text-right py-2">Divergence</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800/50">
                    {signalRows.map((row) => (
                      <tr key={row.date} className="hover:bg-gray-800/30">
                        <td className="py-2 font-medium">{row.date}</td>
                        <td className={`text-right font-bold ${row.total_net_flow_usd >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {formatCurrency(row.total_net_flow_usd)}
                        </td>
                        <td className="text-right text-gray-300">{row.flow_zscore !== null ? row.flow_zscore.toFixed(2) : 'N/A'}</td>
                        <td className="text-right text-amber-400">
                          {row.price_divergence ? row.price_divergence.replace('_', ' ') : row.flow_shock ? 'flow shock' : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center text-gray-500 py-6">No active signals</div>
            )}
          </div>
        </div>

        <div className="space-y-6">
          <div className="card p-6">
            <h3 className="text-sm font-semibold text-gray-400 mb-3">Data Freshness</h3>
            <div className="flex items-center justify-between text-sm">
              <div>
                <div className="text-xs text-gray-500">Last Update</div>
                <div className="text-gray-200 font-semibold">
                  {analytics?.meta.last_update_time
                    ? new Date(analytics.meta.last_update_time).toLocaleString('en-US')
                    : 'N/A'}
                </div>
              </div>
              <div
                className={`px-3 py-1 rounded-full text-xs font-bold ${
                  analytics?.meta.quality_status === 'fresh'
                    ? 'bg-green-500/15 text-green-400'
                    : 'bg-red-500/15 text-red-400'
                }`}
              >
                {analytics?.meta.quality_status === 'fresh' ? 'Fresh' : 'Stale'}
              </div>
            </div>
            {analytics?.meta.staleness_hours !== null && analytics?.meta.staleness_hours !== undefined && (
              <div className="text-xs text-gray-500 mt-3">
                {analytics.meta.staleness_hours.toFixed(1)}h since last update
              </div>
            )}
          </div>

          <div className="card p-6">
            <h3 className="text-sm font-semibold text-gray-400 mb-3">Derived Signals</h3>
            <div className="space-y-3 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-gray-500">Net Flow (BTC)</span>
                <span className="text-gray-200 font-semibold">{formatBtc(latestRow?.net_flow_btc)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-500">Flow % AUM</span>
                <span className="text-gray-200 font-semibold">{formatPct(latestRow?.flow_pct_aum)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-500">Flow vs 20D Avg</span>
                <span className="text-gray-200 font-semibold">{formatMultiple(latestRow?.flow_pct_20d_avg)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-500">Flow Shock</span>
                <span className={`font-semibold ${latestRow?.flow_shock ? 'text-amber-400' : 'text-gray-400'}`}>
                  {latestRow?.flow_shock ? 'Yes' : 'No'}
                </span>
              </div>
            </div>
          </div>

          <div className="card p-6">
            <h3 className="text-sm font-semibold text-gray-400 mb-3">Top Issuers ({timeframe}D)</h3>
            {issuersLoading ? (
              <div className="h-48 bg-gray-800/30 rounded animate-pulse"></div>
            ) : topIssuers && topIssuers.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-gray-500 border-b border-gray-800">
                    <tr>
                      <th className="text-left py-2">Issuer</th>
                      <th className="text-right py-2">Products</th>
                      <th className="text-right py-2">Total Flow</th>
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
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center text-gray-500 py-6">No issuer data available</div>
            )}
          </div>

          <div className="card p-6">
            <h3 className="text-sm font-semibold text-gray-400 mb-3">Top Products ({timeframe}D)</h3>
            {productsLoading ? (
              <div className="h-48 bg-gray-800/30 rounded animate-pulse"></div>
            ) : productLeaders.length > 0 ? (
              <div className="space-y-3">
                {productLeaders.map((product) => (
                  <div key={product.product_code} className="flex items-center justify-between text-sm">
                    <div>
                      <div className="font-semibold text-gray-200">{product.product_code}</div>
                      <div className="text-xs text-gray-500">{product.issuer}</div>
                    </div>
                    <div className={`font-bold ${product.total_flow >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {formatCurrency(product.total_flow)}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center text-gray-500 py-6">No product data available</div>
            )}
          </div>

          <div className="card p-6">
            <h3 className="text-sm font-semibold text-gray-400 mb-3">Flow Extremes ({timeframe}D)</h3>
            {!largestInflow || !largestOutflow ? (
              <div className="text-center text-gray-500 py-6">No flow data available</div>
            ) : (
              <div className="space-y-4 text-sm">
                <div>
                  <div className="text-xs text-gray-500 mb-1">Largest Inflow</div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-200">{largestInflow.date}</span>
                    <span className="font-bold text-green-400">
                      {formatCurrency(largestInflow.total_net_flow_usd)}
                    </span>
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 mb-1">Largest Outflow</div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-200">{largestOutflow.date}</span>
                    <span className="font-bold text-red-400">
                      {formatCurrency(largestOutflow.total_net_flow_usd)}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
