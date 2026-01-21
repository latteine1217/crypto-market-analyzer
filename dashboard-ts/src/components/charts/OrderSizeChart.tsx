'use client';

import React from 'react';
import dynamic from 'next/dynamic';
import { format } from 'date-fns';

const Plot = dynamic(() => import('react-plotly.js'), { 
  ssr: false,
  loading: () => <div className="h-[300px] w-full bg-gray-900/50 animate-pulse rounded-lg flex items-center justify-center text-gray-500">Loading Order Flow...</div>
});

interface OrderSizeData {
  time: string;
  price: number;
  avg_buy_size: number;
  avg_sell_size: number;
  category: string;
}

interface Props {
  data: OrderSizeData[];
  symbol: string;
}

export function OrderSizeChart({ data, symbol }: Props) {
  if (!data || data.length === 0) {
    return (
      <div className="h-[300px] flex items-center justify-center text-gray-500 bg-gray-900/30 rounded-lg border border-gray-800">
        No Order Flow Data Available
      </div>
    );
  }

  const times = data.map(d => d.time);
  const buySizes = data.map(d => d.avg_buy_size);
  const sellSizes = data.map(d => d.avg_sell_size);

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 shadow-xl">
      <div className="flex justify-between items-center mb-4">
        <div>
          <h3 className="text-sm font-bold text-gray-100 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-blue-500"></span>
            Average Order Size (Buy vs Sell)
          </h3>
          <p className="text-[10px] text-gray-500 uppercase tracking-widest">{symbol} • Institutional vs Retail Balance</p>
        </div>
        <div className="flex gap-3 text-[10px]">
           <div className="flex items-center gap-1">
             <div className="w-2 h-2 bg-green-500/80 rounded-sm"></div>
             <span className="text-gray-400">Avg Buy</span>
           </div>
           <div className="flex items-center gap-1">
             <div className="w-2 h-2 bg-red-500/80 rounded-sm"></div>
             <span className="text-gray-400">Avg Sell</span>
           </div>
        </div>
      </div>

      <div className="h-[250px] w-full">
        <Plot
          data={[
            {
              x: times,
              y: buySizes,
              name: 'Avg Buy Size',
              type: 'bar',
              marker: { color: 'rgba(34, 197, 94, 0.6)' },
            },
            {
              x: times,
              y: sellSizes,
              name: 'Avg Sell Size',
              type: 'bar',
              marker: { color: 'rgba(239, 68, 68, 0.6)' },
            }
          ]}
          layout={{
            autosize: true,
            margin: { l: 40, r: 10, t: 10, b: 30 },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            barmode: 'group',
            showlegend: false,
            xaxis: {
              gridcolor: '#222',
              tickfont: { color: '#555', size: 9 },
            },
            yaxis: {
              gridcolor: '#222',
              tickfont: { color: '#555', size: 9 },
              title: { text: 'USD Size', font: { size: 9 } },
              zerolinecolor: '#444'
            },
            hovermode: 'x unified',
          }}
          config={{ responsive: true, displayModeBar: false }}
          style={{ width: '100%', height: '100%' }}
        />
      </div>
      
      <div className="mt-2 text-[9px] text-gray-600 border-t border-gray-800 pt-2 italic">
        * Interpreting: High green bars with falling price suggest whales are absorbing. High red bars with rising price suggest whales are distributing.
      </div>
    </div>
  );
}