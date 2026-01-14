'use client';

import React from 'react';
import dynamic from 'next/dynamic';
import type { OrderSizeData } from '@/lib/api-client';

// Dynamic import for Plotly to avoid SSR issues
const Plot = dynamic(() => import('react-plotly.js'), { 
  ssr: false,
  loading: () => <div className="h-[400px] w-full bg-gray-900/50 animate-pulse rounded-lg flex items-center justify-center text-gray-500">Loading Chart Engine...</div>
});

interface Props {
  data: OrderSizeData[];
  symbol: string;
}

const CATEGORY_COLORS = {
  'Big Whale': '#22c55e',    // Green
  'Small Whale': '#eab308',  // Yellow/Gold
  'Normal': '#9ca3af',       // Gray
  'Retail': '#ef4444',       // Red
};

const CATEGORY_SIZES = {
  'Big Whale': 12,
  'Small Whale': 8,
  'Normal': 6,
  'Retail': 4,
};

export function OrderSizeChart({ data, symbol }: Props) {
  if (!data || data.length === 0) {
    return <div className="h-[400px] flex items-center justify-center text-gray-500 bg-gray-900/30 rounded-lg border border-dashed border-gray-800">No sufficient trade data available for this period</div>;
  }

  // Split data by category for better legend control in Plotly
  const categories = ['Big Whale', 'Small Whale', 'Normal', 'Retail'] as const;
  
  const traces = categories.map(cat => {
    const filtered = data.filter(d => d.category === cat);
    return {
      x: filtered.map(d => d.time),
      y: filtered.map(d => d.price),
      name: cat,
      mode: 'markers' as const,
      type: 'scatter' as const,
      marker: {
        color: CATEGORY_COLORS[cat],
        size: CATEGORY_SIZES[cat],
        opacity: 0.7,
        line: {
          color: 'rgba(0,0,0,0.3)',
          width: 1
        }
      },
      hovertemplate: 
        `<b>${cat}</b><br>` +
        `Time: %{x}<br>` +
        `Price: $%{y:,.2f}<br>` +
        `<extra></extra>`
    };
  });

  return (
    <div className="card border-gray-800/50 bg-gray-900/20 p-4">
      <div className="mb-4 flex justify-between items-center px-2">
        <h3 className="text-lg font-bold text-gray-200">
          {symbol} Spot Average Order Size
        </h3>
        <div className="flex gap-4 text-[10px] font-medium uppercase tracking-tighter">
          {Object.entries(CATEGORY_COLORS).map(([name, color]) => (
            <div key={name} className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }}></span>
              <span className="text-gray-400">{name}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="w-full overflow-hidden rounded-lg bg-[#111827]">
        <Plot
          data={traces}
          layout={{
            autosize: true,
            height: 450,
            margin: { l: 60, r: 20, t: 20, b: 40 },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            showlegend: false,
            hovermode: 'closest',
            xaxis: {
              gridcolor: '#1f2937',
              zeroline: false,
              tickfont: { color: '#6b7280', size: 10 },
              type: 'date'
            },
            yaxis: {
              gridcolor: '#1f2937',
              zeroline: false,
              tickfont: { color: '#6b7280', size: 10 },
              tickformat: '$,.0f',
              title: { text: 'Price (USD)', font: { color: '#4b5563', size: 10 } }
            },
          }}
          config={{
            responsive: true,
            displayModeBar: false,
          }}
          className="w-full"
        />
      </div>
      
      <div className="mt-4 px-2">
        <p className="text-[10px] text-gray-500 italic leading-relaxed">
          * Calculation: (Sum of Quantity / Trade Count) per 1-hour bucket. 
          Thresholds: Big Whale ≥ 0.5 BTC, Small Whale ≥ 0.1 BTC, Normal ≥ 0.02 BTC.
        </p>
      </div>
    </div>
  );
}
