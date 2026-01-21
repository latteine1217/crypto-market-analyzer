'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { FREDIndicatorsChart } from '@/components/FREDIndicatorsChart';
import { FREDSummaryCards } from '@/components/FREDSummaryCards';

const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

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

interface FREDDataPoint {
  timestamp: string;
  value: number;
  forecast: number | null;
}

interface FREDResponse {
  summary: FREDIndicator[];
  data: Record<string, FREDDataPoint[]>;
  metadata: {
    days_requested: number;
    series_count: number;
    total_records: number;
  };
}

export default function FREDPage() {
  const [timeRange, setTimeRange] = useState<number>(180); // 預設 6 個月
  const [selectedSeries, setSelectedSeries] = useState<string[]>([
    'UNRATE',
    'CPIAUCSL',
    'FEDFUNDS',
    'GDP'
  ]);

  const { data, isLoading, error } = useQuery<FREDResponse>({
    queryKey: ['fredIndicators', selectedSeries.join(','), timeRange],
    queryFn: async () => {
      const response = await fetch(
        `${apiUrl}/fred/indicators?series=${selectedSeries.join(',')}&days=${timeRange}`
      );
      if (!response.ok) throw new Error('Failed to fetch FRED data');
      const json = await response.json();
      return json.data;
    },
    refetchInterval: 60000 * 15, // 每 15 分鐘更新
  });

  const timeRangeOptions = [
    { label: '3M', value: 90 },
    { label: '6M', value: 180 },
    { label: '1Y', value: 365 },
    { label: 'All', value: 1825 }, // 5 年
  ];

  const availableSeries = [
    { id: 'UNRATE', name: 'Unemployment Rate', category: 'Labor' },
    { id: 'CPIAUCSL', name: 'Consumer Price Index', category: 'Inflation' },
    { id: 'FEDFUNDS', name: 'Federal Funds Rate', category: 'Monetary Policy' },
    { id: 'GDP', name: 'Gross Domestic Product', category: 'Growth' },
  ];

  const toggleSeries = (seriesId: string) => {
    setSelectedSeries((prev) =>
      prev.includes(seriesId)
        ? prev.filter((id) => id !== seriesId)
        : [...prev, seriesId]
    );
  };

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div>
          <h1 className="text-4xl font-bold mb-2 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">
            FRED Economic Indicators
          </h1>
          <p className="text-gray-400">
            Key macroeconomic data from the Federal Reserve Economic Data (FRED) database
          </p>
        </div>
        
        {/* Time Range Selector */}
        <div className="flex gap-2">
          {timeRangeOptions.map((option) => (
            <button
              key={option.value}
              onClick={() => setTimeRange(option.value)}
              className={`px-4 py-2 rounded-lg font-medium transition-all ${
                timeRange === option.value
                  ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {/* Series Selector */}
      <div className="card p-4">
        <h3 className="text-sm font-medium text-gray-400 mb-3">Select Indicators</h3>
        <div className="flex flex-wrap gap-2">
          {availableSeries.map((series) => (
            <button
              key={series.id}
              onClick={() => toggleSeries(series.id)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                selectedSeries.includes(series.id)
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              <span className="mr-2">{series.name}</span>
              <span className="text-xs opacity-75">({series.category})</span>
            </button>
          ))}
        </div>
        <p className="text-xs text-gray-500 mt-2">
          Select at least one indicator to display on the chart
        </p>
      </div>

      {/* Summary Cards */}
      {isLoading && (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      )}

      {error && (
        <div className="card p-6 border-red-500/20">
          <p className="text-red-400">⚠️ Error loading FRED data: {(error as Error).message}</p>
        </div>
      )}

      {data && (
        <>
          <FREDSummaryCards summary={data.summary} />
          
          {/* Main Chart */}
          <div className="card p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">Economic Indicators Trends</h2>
              <div className="text-sm text-gray-400">
                Showing {data.metadata.total_records} data points over {data.metadata.days_requested} days
              </div>
            </div>
            
            {selectedSeries.length === 0 ? (
              <div className="text-center py-12 text-gray-400">
                <p>Please select at least one indicator to display the chart</p>
              </div>
            ) : (
              <FREDIndicatorsChart 
                data={data.data} 
                selectedSeries={selectedSeries}
                seriesInfo={availableSeries}
              />
            )}
          </div>

          {/* Data Info */}
          <div className="card p-4 bg-blue-900/10 border-blue-500/20">
            <div className="flex items-start gap-3">
              <span className="text-2xl">ℹ️</span>
              <div>
                <h3 className="font-medium text-blue-400 mb-1">About FRED Data</h3>
                <p className="text-sm text-gray-400">
                  Data is sourced from the Federal Reserve Economic Data (FRED) API. 
                  Updates are collected weekly (every Monday at 12:00 PM). 
                  Historical data availability varies by indicator.
                </p>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
