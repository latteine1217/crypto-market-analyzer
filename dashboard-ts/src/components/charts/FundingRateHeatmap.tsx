'use client';

import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { format } from 'date-fns';

interface HeatmapData {
  times: string[];
  symbols: string[];
  points: Array<{ t: number; s: number; v: number }>;
}

interface HeatmapRow {
  symbol: string;
  values: Array<number | null>;
}

const MAX_COLUMNS = 36;

function colorForRate(value: number | null, scale: number): string {
  if (value === null || Number.isNaN(value)) {
    return 'rgba(148, 163, 184, 0.08)';
  }

  const intensity = Math.min(Math.abs(value) / scale, 1);
  const alpha = 0.2 + intensity * 0.7;

  if (value > 0) {
    return `rgba(239, 68, 68, ${alpha})`;
  }
  if (value < 0) {
    return `rgba(34, 197, 94, ${alpha})`;
  }
  return 'rgba(148, 163, 184, 0.22)';
}

const FundingRateHeatmap: React.FC = () => {
  const [data, setData] = useState<HeatmapData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    const fetchData = async () => {
      try {
        const response = await axios.get('/api/derivatives/funding-rate/heatmap?hours=168&limit=10'); // 7 days, top 10
        if (mounted) {
          setData(response.data.data);
        }
      } catch (error) {
        console.error('Failed to fetch funding heatmap:', error);
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    fetchData();

    return () => {
      mounted = false;
    };
  }, []);

  const heatmapData = useMemo(() => {
    if (!data || data.symbols.length === 0 || data.times.length === 0) {
      return null;
    }

    const step = Math.max(1, Math.ceil(data.times.length / MAX_COLUMNS));
    const sampledTimes = data.times.filter((_, idx) => idx % step === 0);

    const rowTemplate: HeatmapRow[] = data.symbols.map(symbol => ({
      symbol,
      values: new Array(sampledTimes.length).fill(null),
    }));

    for (const point of data.points) {
      const sampledIndex = Math.floor(point.t / step);
      if (!rowTemplate[point.s] || sampledIndex < 0 || sampledIndex >= sampledTimes.length) continue;
      rowTemplate[point.s].values[sampledIndex] = point.v;
    }

    const flatValues = rowTemplate.flatMap(row => row.values).filter((v): v is number => v !== null);
    const absMax = flatValues.length > 0
      ? flatValues.reduce((m, v) => Math.max(m, Math.abs(v)), 0)
      : 0.0001;

    const scale = Math.max(absMax, 0.0001);
    const tickEvery = Math.max(1, Math.ceil(sampledTimes.length / 8));

    return {
      rows: rowTemplate,
      times: sampledTimes,
      scale,
      tickEvery,
    };
  }, [data]);

  if (loading) {
    return <div className="card h-[320px] flex items-center justify-center text-sm text-gray-400">Loading funding heatmap...</div>;
  }
  if (!heatmapData) {
    return <div className="card h-[320px] flex items-center justify-center text-sm text-gray-400">No funding heatmap data</div>;
  }

  const { rows, times, scale, tickEvery } = heatmapData;
  const gridTemplate = { gridTemplateColumns: `repeat(${times.length}, minmax(14px, 1fr))` };

  return (
    <div className="card p-4 md:p-5 space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-lg md:text-xl font-black tracking-tight text-gray-100">Funding Rate Heatmap (8h Bucket)</h3>
          <p className="text-xs text-gray-500 mt-1">Red = Long crowded, Green = Short crowded</p>
        </div>
        <div className="text-right text-[11px] text-gray-500 shrink-0">
          <div>Dynamic scale</div>
          <div className="font-mono text-gray-300">±{(scale * 100).toFixed(3)}%</div>
        </div>
      </div>

      <div className="overflow-x-auto pb-1">
        <div className="min-w-[760px] space-y-2">
          {rows.map((row) => (
            <div key={row.symbol} className="grid grid-cols-[110px_1fr] items-center gap-3">
              <div className="text-sm font-bold text-gray-200 tracking-wide">{row.symbol}</div>
              <div className="grid gap-1" style={gridTemplate}>
                {row.values.map((value, idx) => (
                  <div
                    key={`${row.symbol}-${idx}`}
                    className="h-6 rounded-[4px] border border-white/5 transition-colors"
                    style={{ backgroundColor: colorForRate(value, scale) }}
                    title={`${row.symbol} | ${format(new Date(times[idx]), 'MM-dd HH:mm')} | ${value === null ? 'No data' : `${(value * 100).toFixed(4)}%`}`}
                  />
                ))}
              </div>
            </div>
          ))}

          <div className="grid grid-cols-[110px_1fr] gap-3 pt-1">
            <div />
            <div className="grid gap-1" style={gridTemplate}>
              {times.map((t, idx) => (
                <div key={`tick-${idx}`} className="text-[10px] text-gray-500 text-center whitespace-nowrap">
                  {idx % tickEvery === 0 ? format(new Date(t), 'MM/dd HH:mm') : ''}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 text-[11px] text-gray-400">
        <div className="rounded-md border border-green-500/30 bg-green-500/10 px-2 py-1 text-center">Negative (Short crowded)</div>
        <div className="rounded-md border border-slate-500/30 bg-slate-500/10 px-2 py-1 text-center">Neutral</div>
        <div className="rounded-md border border-red-500/30 bg-red-500/10 px-2 py-1 text-center">Positive (Long crowded)</div>
      </div>
    </div>
  );
};

export default FundingRateHeatmap;
