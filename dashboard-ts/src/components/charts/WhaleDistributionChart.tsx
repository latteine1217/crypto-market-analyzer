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

interface WhaleDistributionChartProps {
  symbol?: string;
}

export const WhaleDistributionChart: React.FC<WhaleDistributionChartProps> = ({ symbol = 'BTC' }) => {
  const [data, setData] = useState<WhaleData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const res = await fetch(`/api/blockchain/${symbol}/rich-list?days=30`);
        const json = await res.json();
        setData(json.data);
      } catch (e) {
        console.error('Failed to load whale data', e);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [symbol]);

  // 我們只取最新的快照來畫分佈圖 (圓餅圖或柱狀圖)
  const latestTime = data.length > 0 ? data[data.length - 1].timestamp : '';
  const latestSnapshot = React.useMemo(() => 
    data.filter(d => d.timestamp === latestTime), 
    [data, latestTime]
  );

  // 1. 處理圓餅圖數據：過濾並合併小額地址
  const pieData = React.useMemo(() => {
    if (!latestSnapshot || latestSnapshot.length === 0) return { values: [], labels: [], colors: [] };

    let retailBalance = 0;
    const meaningfulTiers: WhaleData[] = [];

    // 定義排序權重 (從大到小)
    const tierOrder: Record<string, number> = {
      '[100,000 - 1,000,000)': 100,
      '[10,000 - 100,000)': 90,
      '[1,000 - 10,000)': 80,
      '[100 - 1,000)': 70,
      '[10 - 100)': 60,
      '[1 - 10)': 50,
    };

    latestSnapshot.forEach(d => {
      if (!d) return;
      // 判斷是否為小額 (小於 1 BTC)
      const tierName = d.tier_name || '';
      if (tierName.includes('0.1') || tierName.includes('0.01') || tierName.includes('0.001') || tierName.includes('0.0001')) {
        retailBalance += d.total_balance;
      } else {
        meaningfulTiers.push(d);
      }
    });

    // 根據權重排序
    meaningfulTiers.sort((a, b) => {
      const aTier = a?.tier_name || '';
      const bTier = b?.tier_name || '';
      return (tierOrder[bTier] || 0) - (tierOrder[aTier] || 0);
    });

    const values = meaningfulTiers.map(d => d?.total_balance || 0);
    const labels = meaningfulTiers.map(d => d?.tier_name || 'Unknown');
    
    // 加上合併後的 Retail
    if (retailBalance > 0) {
      values.push(retailBalance);
      labels.push('Retail (< 1 BTC)');
    }

    return {
      values,
      labels,
      // 使用冷色調漸層代表機構，暖色代表散戶
      colors: [
        '#3b82f6', // >100k (Blue)
        '#6366f1', // 10k-100k (Indigo)
        '#8b5cf6', // 1k-10k (Purple - Whale)
        '#ec4899', // 100-1k (Pink)
        '#f43f5e', // 10-100 (Rose)
        '#f97316', // 1-10 (Orange)
        '#84cc16'  // Retail (Lime)
      ]
    };
  }, [latestSnapshot]);

  if (loading || data.length === 0) return <div className="h-[400px] animate-pulse bg-gray-900 rounded-xl" />;

  // 2. 處理折線圖數據
  const whaleTier = data.filter(d => d && (d.tier_name || '').includes('1,000 - 10,000'));
  // 簡單去重 (如果同一時間點有多筆)
  const uniqueWhaleData = Array.from(new Map(whaleTier.filter(item => item && item.timestamp).map(item => [item.timestamp, item])).values())
    .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

  const whaleTimes = uniqueWhaleData.map(d => d.timestamp);
  const whaleCounts = uniqueWhaleData.map(d => d.address_count);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 h-full">
      {/* 1. 當前持倉分佈 */}
      <div className="bg-gray-900 p-4 rounded-xl border border-gray-800 flex flex-col">
        <h3 className="text-sm font-bold text-gray-100 mb-2">BTC Balance Distribution (Latest)</h3>
        <div className="flex-1 min-h-0 relative">
          <Plot
            data={[{
              values: pieData.values,
              labels: pieData.labels,
              type: 'pie',
              hole: 0.5,
              marker: { colors: pieData.colors },
              textinfo: 'percent', // 圖上只顯示百分比
              hoverinfo: 'label+value+percent',
              textposition: 'outside'
            }]}
            layout={{
              autosize: true,
              paper_bgcolor: 'rgba(0,0,0,0)',
              plot_bgcolor: 'rgba(0,0,0,0)',
              showlegend: true,
              // 圖例放底部，橫向排列
              legend: { 
                orientation: 'h', 
                x: 0, 
                y: -0.1, 
                font: { color: '#9ca3af', size: 9 },
                itemwidth: 80
              },
              margin: { l: 20, r: 20, t: 20, b: 60 }
            }}
            config={{ responsive: true, displayModeBar: false }}
            style={{ width: '100%', height: '100%' }}
          />
        </div>
      </div>

      {/* 2. 巨鯨地址變化趨勢 (1k - 10k BTC) */}
      <div className="bg-gray-900 p-4 rounded-xl border border-gray-800 flex flex-col">
        <h3 className="text-sm font-bold text-gray-100 mb-2">Whale Addresses Trend (1k - 10k BTC)</h3>
        <div className="flex-1 min-h-0 relative">
          {whaleCounts.length > 1 ? (
            <Plot
              data={[{
                x: whaleTimes,
                y: whaleCounts,
                type: 'scatter',
                mode: 'lines+markers',
                line: { color: '#8b5cf6', width: 3, shape: 'spline' }, // 使用紫色代表巨鯨
                fill: 'tozeroy',
                fillcolor: 'rgba(139, 92, 246, 0.1)',
                marker: { size: 4 }
              }]}
              layout={{
                autosize: true,
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                xaxis: { 
                  gridcolor: '#222', 
                  tickfont: { color: '#666', size: 10 },
                  tickformat: '%H:%M' // 格式化時間
                },
                yaxis: { 
                  gridcolor: '#222', 
                  tickfont: { color: '#666', size: 10 },
                  autorange: true 
                },
                margin: { l: 35, r: 10, t: 10, b: 30 }
              }}
              config={{ responsive: true, displayModeBar: false }}
              style={{ width: '100%', height: '100%' }}
            />
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-500 space-y-2">
              <span className="text-2xl">📡</span>
              <span className="text-xs font-mono">Collecting data points... ({whaleCounts.length}/2)</span>
              <span className="text-[10px] text-gray-600">Trend will appear after next snapshot (10m)</span>
            </div>
          )}
        </div>
        <p className="text-[10px] text-gray-600 mt-2 italic flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-purple-500"></span>
          Accumulating trend = Institutional Buy Signal
        </p>
      </div>
    </div>
  );
};
