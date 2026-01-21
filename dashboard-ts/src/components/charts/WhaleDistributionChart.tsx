'use client';

import React, { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { format } from 'date-fns';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface WhaleData {
  timestamp: string;
  tier_name: string;
  address_count: number;
  total_balance: number;
}

export const WhaleDistributionChart: React.FC = () => {
  const [data, setData] = useState<WhaleData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const res = await fetch('/api/blockchain/BTC/rich-list?days=30');
        const json = await res.json();
        setData(json.data);
      } catch (e) {
        console.error('Failed to load whale data', e);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  if (loading || data.length === 0) return <div className="h-[400px] animate-pulse bg-gray-900 rounded-xl" />;

  // 我們只取最新的快照來畫分佈圖 (圓餅圖或柱狀圖)
  const latestTime = data[data.length - 1].timestamp;
  const latestSnapshot = data.filter(d => d.timestamp === latestTime);

  // 另外，我們想看 1k-10k BTC 地址隨時間的變化 (折線圖)
  const whaleTier = data.filter(d => d.tier_name.includes('1,000 - 10,000'));
  const whaleTimes = whaleTier.map(d => d.timestamp);
  const whaleCounts = whaleTier.map(d => d.address_count);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* 1. 當前持倉分佈 */}
      <div className="bg-gray-900 p-4 rounded-xl border border-gray-800">
        <h3 className="text-sm font-bold text-gray-100 mb-4">BTC Balance Distribution (Latest)</h3>
        <div className="h-[300px]">
          <Plot
            data={[{
              values: latestSnapshot.map(d => d.total_balance),
              labels: latestSnapshot.map(d => d.tier_name),
              type: 'pie',
              hole: 0.4,
              marker: { colors: ['#3b82f6', '#22c55e', '#eab308', '#f97316', '#ef4444'] }
            }]}
            layout={{
              autosize: true,
              paper_bgcolor: 'rgba(0,0,0,0)',
              plot_bgcolor: 'rgba(0,0,0,0)',
              showlegend: true,
              legend: { font: { color: '#9ca3af', size: 10 } },
              margin: { l: 0, r: 0, t: 0, b: 0 }
            }}
            config={{ responsive: true, displayModeBar: false }}
            style={{ width: '100%', height: '100%' }}
          />
        </div>
      </div>

      {/* 2. 巨鯨地址變化趨勢 (1k - 10k BTC) */}
      <div className="bg-gray-900 p-4 rounded-xl border border-gray-800">
        <h3 className="text-sm font-bold text-gray-100 mb-4">Whale Addresses Trend (1k - 10k BTC)</h3>
        <div className="h-[300px]">
          <Plot
            data={[{
              x: whaleTimes,
              y: whaleCounts,
              type: 'scatter',
              mode: 'lines+markers',
              line: { color: '#3b82f6', width: 3 },
              fill: 'tozeroy',
              fillcolor: 'rgba(59, 130, 246, 0.1)'
            }]}
            layout={{
              autosize: true,
              paper_bgcolor: 'rgba(0,0,0,0)',
              plot_bgcolor: 'rgba(0,0,0,0)',
              xaxis: { gridcolor: '#222', tickfont: { color: '#666' } },
              yaxis: { gridcolor: '#222', tickfont: { color: '#666' } },
              margin: { l: 40, r: 20, t: 10, b: 40 }
            }}
            config={{ responsive: true, displayModeBar: false }}
            style={{ width: '100%', height: '100%' }}
          />
        </div>
        <p className="text-[10px] text-gray-600 mt-2 italic">
          * Increasing whale addresses often signals accumulation by institutional players.
        </p>
      </div>
    </div>
  );
};
