'use client';

import React, { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { fetchOBI, OBIData } from '@/lib/api-client';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface OBIChartProps {
  exchange: string;
  symbol: string;
}

export const OBIChart: React.FC<OBIChartProps> = ({ exchange, symbol }) => {
  const [data, setData] = useState<OBIData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        const obiData = await fetchOBI(exchange, symbol, 300);
        setData(obiData);
      } catch (error) {
        console.error('Failed to load OBI data', error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
    const timer = window.setInterval(loadData, 30000); // Update every 30s
    return () => clearInterval(timer);
  }, [exchange, symbol]);

  if (loading && data.length === 0) {
    return (
      <div className="h-[300px] w-full bg-gray-900/50 rounded-xl animate-pulse flex items-center justify-center">
        <span className="text-gray-500">Loading OBI Data...</span>
      </div>
    );
  }

  const times = data.map(d => d.time);
  const obiValues = data.map(d => d.obi);
  
  // Color bars based on imbalance side
  const colors = obiValues.map(v => v >= 0 ? 'rgba(0, 227, 150, 0.6)' : 'rgba(239, 68, 68, 0.6)');

  return (
    <div className="w-full h-full bg-gray-900 rounded-xl border border-gray-800 shadow-xl overflow-hidden">
      <div className="p-4 border-b border-gray-800 flex justify-between items-center bg-gray-900/50 backdrop-blur">
        <div>
          <h3 className="text-lg font-bold text-gray-100 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-blue-500"></span>
            Order Book Imbalance (OBI)
          </h3>
          <p className="text-xs text-gray-500 font-mono">
            {symbol} • Top 20 Levels Notional Imbalance
          </p>
        </div>
      </div>
      
      <div className="h-[250px] w-full p-2">
        <Plot
          data={[
            {
              x: times,
              y: obiValues,
              type: 'bar',
              name: 'OBI',
              marker: { color: colors },
            }
          ]}
          layout={{
            autosize: true,
            margin: { l: 40, r: 20, t: 10, b: 40 },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            showlegend: false,
            xaxis: {
              showgrid: false,
              tickfont: { color: '#666' },
            },
            yaxis: {
              range: [-1, 1],
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
            displayModeBar: false 
          }}
          style={{ width: '100%', height: '100%' }}
        />
      </div>
      <div className="px-4 pb-2 flex justify-between text-[10px] text-gray-500 font-mono">
        <span>SELL HEAVY (-1.0)</span>
        <span>NEUTRAL (0)</span>
        <span>BUY HEAVY (+1.0)</span>
      </div>
    </div>
  );
};
