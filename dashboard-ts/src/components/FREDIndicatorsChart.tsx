'use client';

import React, { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface FREDDataPoint {
  timestamp: string;
  value: number;
  forecast: number | null;
}

interface SeriesInfo {
  id: string;
  name: string;
  category: string;
}

interface Props {
  data: Record<string, FREDDataPoint[]>;
  selectedSeries: string[];
  seriesInfo: SeriesInfo[];
}

// 為每個指標定義顏色
const seriesColors: Record<string, string> = {
  UNRATE: '#ef4444', // 失業率 - 紅色
  CPIAUCSL: '#f59e0b', // CPI - 橙色
  FEDFUNDS: '#3b82f6', // 聯邦基金利率 - 藍色
  GDP: '#10b981', // GDP - 綠色
  DGS10: '#8b5cf6', // 10年期國債 - 紫色
  DEXUSEU: '#ec4899', // EUR/USD - 粉色
  DCOILWTICO: '#14b8a6', // 原油 - 青色
};

export function FREDIndicatorsChart({ data, selectedSeries, seriesInfo }: Props) {
  // 將多個指標的資料合併成單一時間序列
  const chartData = useMemo(() => {
    if (!data || selectedSeries.length === 0) return [];

    // 收集所有時間戳
    const timestampMap = new Map<string, Record<string, number>>();

    selectedSeries.forEach((seriesId) => {
      const seriesData = data[seriesId] || [];
      seriesData.forEach((point) => {
        const dateKey = new Date(point.timestamp).toISOString().split('T')[0];
        if (!timestampMap.has(dateKey)) {
          timestampMap.set(dateKey, {});
        }
        const record = timestampMap.get(dateKey)!;
        record[seriesId] = point.value;
      });
    });

    // 轉換為陣列並排序
    return Array.from(timestampMap.entries())
      .map(([date, values]) => ({
        date,
        ...values,
      }))
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [data, selectedSeries]);

  if (chartData.length === 0) {
    return (
      <div className="flex items-center justify-center h-96 text-gray-400">
        No data available for the selected indicators
      </div>
    );
  }

  // Custom Tooltip
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-gray-900 border border-gray-700 rounded-lg p-3 shadow-xl">
          <p className="text-sm text-gray-400 mb-2">{label}</p>
          {payload.map((entry: any, index: number) => {
            const seriesName = seriesInfo.find((s) => s.id === entry.dataKey)?.name || entry.dataKey;
            return (
              <div key={index} className="flex items-center gap-2 text-sm">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: entry.color }}
                />
                <span className="text-gray-300">{seriesName}:</span>
                <span className="font-bold" style={{ color: entry.color }}>
                  {typeof entry.value === 'number' ? entry.value.toFixed(2) : 'N/A'}
                </span>
              </div>
            );
          })}
        </div>
      );
    }
    return null;
  };

  return (
    <ResponsiveContainer width="100%" height={500}>
      <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis
          dataKey="date"
          stroke="#9ca3af"
          tick={{ fill: '#9ca3af', fontSize: 12 }}
          tickFormatter={(value) => {
            const date = new Date(value);
            return date.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
          }}
        />
        <YAxis
          stroke="#9ca3af"
          tick={{ fill: '#9ca3af', fontSize: 12 }}
          tickFormatter={(value) => value.toFixed(1)}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ paddingTop: '20px' }}
          formatter={(value) => {
            const seriesName = seriesInfo.find((s) => s.id === value)?.name || value;
            return <span className="text-gray-300 text-sm">{seriesName}</span>;
          }}
        />
        {selectedSeries.map((seriesId) => (
          <Line
            key={seriesId}
            type="monotone"
            dataKey={seriesId}
            stroke={seriesColors[seriesId] || '#6b7280'}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 6 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
