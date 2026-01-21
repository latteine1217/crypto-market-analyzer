'use client';

import React, { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { fetchCVD, CVDData } from '@/lib/api-client';
import { format } from 'date-fns';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface CVDChartProps {
  exchange: string;
  symbol: string;
}

export const CVDChart: React.FC<CVDChartProps> = ({ exchange, symbol }) => {
  const [data, setData] = useState<CVDData[]>([]);
  const [loading, setLoading] = useState(true);
  const [interval, setInterval] = useState('1m');

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        const cvdData = await fetchCVD(exchange, symbol, interval, 500);
        setData(cvdData);
      } catch (error) {
        console.error('Failed to load CVD data', error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
    const timer = window.setInterval(loadData, 60000); // Update every minute
    return () => clearInterval(timer);
  }, [exchange, symbol, interval]);

  if (loading && data.length === 0) {
    return (
      <div className="h-[400px] w-full bg-gray-900/50 rounded-xl animate-pulse flex items-center justify-center">
        <span className="text-gray-500">Loading CVD Data...</span>
      </div>
    );
  }

  // Check if we have data
  if (data.length === 0) {
    return (
      <div className="h-[400px] w-full bg-gray-900/50 rounded-xl flex items-center justify-center border border-gray-800">
        <div className="text-center">
          <p className="text-gray-400 mb-2">No CVD data available</p>
          <p className="text-xs text-gray-600">Waiting for trades to accumulate...</p>
        </div>
      </div>
    );
  }

  // Data preparation
  const times = data.map(d => d.time);
  
  // ✅ 基準線對齊 (Baseline Alignment)
  // 將第一筆資料設為 0，後續以此類推，這樣可以清晰看到這段時間內的相對累積變化
  const firstValue = data.length > 0 ? Number(data[0].cvd) : 0;
  const cvdValues = data.map(d => Number(d.cvd) - firstValue);
  
  // Color logic: Green if net positive, Red if net negative for this session
  const latestCVD = cvdValues[cvdValues.length - 1];
  const lineColor = latestCVD >= 0 ? '#00E396' : '#EF4444'; 

  return (
    <div className="w-full h-full bg-gray-900 rounded-xl border border-gray-800 shadow-xl overflow-hidden">
      <div className="p-4 border-b border-gray-800 flex justify-between items-center bg-gray-900/50 backdrop-blur">
        <div>
          <h3 className="text-lg font-bold text-gray-100 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#00E396]"></span>
            Cumulative Volume Delta (CVD)
          </h3>
          <p className="text-xs text-gray-500 font-mono">
            {symbol} • {exchange.toUpperCase()} • {interval}
          </p>
        </div>
        <div className="flex gap-2">
           {/* Interval Selector Placeholder */}
           <span className="text-xs bg-gray-800 px-2 py-1 rounded text-gray-400">Live</span>
        </div>
      </div>
      
      <div className="h-[350px] w-full p-2">
        <Plot
          data={[
            {
              x: times,
              y: cvdValues,
              type: 'scatter',
              mode: 'lines',
              name: 'CVD',
              line: { color: lineColor, width: 2 },
              fill: 'tozeroy',
              fillcolor: 'rgba(0, 227, 150, 0.1)'
            }
          ]}
          layout={{
            autosize: true,
            margin: { l: 50, r: 20, t: 10, b: 40 },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            showlegend: false,
            xaxis: {
              showgrid: true,
              gridcolor: '#333',
              tickfont: { color: '#666' },
              // rangeslider: { visible: false }
            },
            yaxis: {
              showgrid: true,
              gridcolor: '#333',
              tickfont: { color: '#666' },
              zeroline: true,
              zerolinecolor: '#444'
            },
            hovermode: 'x unified',
          }}
          config={{ 
            responsive: true, 
            displayModeBar: false,
            scrollZoom: false 
          }}
          style={{ width: '100%', height: '100%' }}
        />
      </div>
    </div>
  );
};
