'use client';

import React, { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import axios from 'axios';
import { format } from 'date-fns';

// 動態載入 Plotly，禁用 SSR
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface HeatmapData {
  times: string[];
  symbols: string[];
  matrix: (number | null)[][];
}

const FundingRateHeatmap: React.FC = () => {
  const [data, setData] = useState<HeatmapData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.get('/api/derivatives/funding-rate/heatmap?hours=168&limit=10'); // 7 days, top 10
        setData(response.data.data);
      } catch (error) {
        console.error('Failed to fetch funding heatmap:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) return <div className="h-96 flex items-center justify-center bg-gray-900 rounded-lg">Loading Heatmap...</div>;
  if (!data || data.symbols.length === 0) return <div className="h-96 flex items-center justify-center bg-gray-900 rounded-lg">No data available</div>;

  // 格式化時間標籤
  const formattedTimes = data.times.map(t => format(new Date(t), 'MM-dd HH:mm'));

  return (
    <div className="bg-gray-900 p-4 rounded-lg shadow-xl">
      <h3 className="text-xl font-bold mb-4 text-white">Funding Rate Heatmap (8h Bucket)</h3>
      <div className="w-full h-[500px]">
        <Plot
          data={[
            {
              z: data.matrix,
              x: formattedTimes,
              y: data.symbols,
              type: 'heatmap',
              colorscale: [
                [0, '#00ff00'],     // 深綠 (Negative)
                [0.45, '#1a1a1a'],  // 灰色 (Near Zero)
                [0.55, '#1a1a1a'],  // 灰色
                [1, '#ff0000']      // 深紅 (Positive)
              ],
              zmin: -0.0003, // -0.03%
              zmax: 0.0003,  // 0.03% (通常 0.01% 是基準，0.03% 以上算過熱)
              colorbar: {
                title: { text: 'Rate' },
                tickformat: '.2%',
                thickness: 20
              },
              hovertemplate: '<b>%{y}</b><br>Time: %{x}<br>Rate: %{z:.4%}<extra></extra>'
            }
          ]}
          layout={{
            autosize: true,
            margin: { l: 80, r: 20, t: 10, b: 80 },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            xaxis: {
              tickangle: -45,
              gridcolor: '#333',
              tickfont: { color: '#ccc' }
            },
            yaxis: {
              gridcolor: '#333',
              tickfont: { color: '#ccc' },
              autorange: 'reversed' // 讓 BTCUSDT 在最上方
            }
          }}
          config={{ responsive: true, displayModeBar: false }}
          style={{ width: '100%', height: '100%' }}
        />
      </div>
      <div className="mt-2 text-xs text-gray-500 flex justify-between">
        <span>🟢 Negative (Short Overcrowded)</span>
        <span>⚪ Neutral</span>
        <span>🔴 Positive (Long Overcrowded)</span>
      </div>
    </div>
  );
};

export default FundingRateHeatmap;
