'use client';

import React from 'react';

interface FREDIndicator {
  series_id: string;
  name: string;
  latest_value: number | null;
  previous_value: number | null;
  change: number | null;
  change_percent: string | null;
  timestamp: string | null;
  unit: string;
}

interface Props {
  summary: FREDIndicator[];
}

// 圖示對應
const seriesIcons: Record<string, string> = {
  UNRATE: '📉',
  CPIAUCSL: '📊',
  FEDFUNDS: '💰',
  GDP: '📈',
  DGS10: '🏦',
  DEXUSEU: '💱',
  DCOILWTICO: '🛢️',
};

// 判斷數值是好是壞的邏輯（不同指標有不同判斷標準）
function getChangeColor(seriesId: string, change: number | null): string {
  if (change === null) return 'text-gray-400';
  
  // 失業率：下降是好事
  if (seriesId === 'UNRATE') {
    return change < 0 ? 'text-green-400' : 'text-red-400';
  }
  
  // CPI：上升過快是壞事
  if (seriesId === 'CPIAUCSL') {
    return Math.abs(change) < 1 ? 'text-green-400' : 'text-red-400';
  }
  
  // 聯邦基金利率：根據情境不同
  if (seriesId === 'FEDFUNDS') {
    return change > 0 ? 'text-red-400' : 'text-green-400';
  }
  
  // GDP：增長是好事
  if (seriesId === 'GDP') {
    return change > 0 ? 'text-green-400' : 'text-red-400';
  }
  
  // 預設：上升綠色，下降紅色
  return change > 0 ? 'text-green-400' : 'text-red-400';
}

export function FREDSummaryCards({ summary }: Props) {
  if (!summary || summary.length === 0) {
    return (
      <div className="text-center py-6 text-gray-400">
        No summary data available
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {summary.map((indicator) => {
        const icon = seriesIcons[indicator.series_id] || '📊';
        const changeColor = getChangeColor(indicator.series_id, indicator.change);
        const isPositive = indicator.change !== null && indicator.change > 0;

        return (
          <div
            key={indicator.series_id}
            className="card p-4 hover:border-blue-500/30 transition-all"
          >
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="text-2xl">{icon}</span>
                <div>
                  <h3 className="text-sm font-medium text-gray-400">
                    {indicator.name}
                  </h3>
                  <p className="text-xs text-gray-500">{indicator.series_id}</p>
                </div>
              </div>
            </div>

            {/* Value */}
            <div className="mb-2">
              {indicator.latest_value !== null ? (
                <div className="text-3xl font-bold text-white">
                  {indicator.latest_value.toFixed(2)}
                  <span className="text-sm text-gray-400 ml-1">{indicator.unit}</span>
                </div>
              ) : (
                <div className="text-2xl text-gray-500">No data</div>
              )}
            </div>

            {/* Change */}
            {indicator.change !== null && indicator.change_percent !== null && (
              <div className="flex items-center gap-2">
                <span className={`text-sm font-medium ${changeColor}`}>
                  {isPositive ? '▲' : '▼'} {Math.abs(indicator.change).toFixed(2)} 
                  ({isPositive ? '+' : ''}{indicator.change_percent}%)
                </span>
              </div>
            )}

            {/* Timestamp */}
            {indicator.timestamp && (
              <div className="mt-2 text-xs text-gray-500">
                Updated: {new Date(indicator.timestamp).toLocaleDateString('en-US', {
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric',
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
