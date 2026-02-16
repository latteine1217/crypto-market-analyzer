'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchFearGreed } from '@/lib/api-client';
import { QUERY_PROFILES } from '@/lib/queryProfiles';

export function FearGreedWidget() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['fearGreed'],
    queryFn: fetchFearGreed,
    ...QUERY_PROFILES.slow,
  });

  if (isLoading) {
    return (
      <div className="card border-gray-800/50 animate-pulse">
        <div className="p-6">
          <div className="h-8 bg-gray-800 rounded w-1/2 mb-4"></div>
          <div className="h-32 bg-gray-800 rounded"></div>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="card border-red-500/50">
        <div className="p-6 text-center text-red-400">
          ⚠️ Failed to load Fear & Greed Index
        </div>
      </div>
    );
  }

  // 根據數值決定顏色
  const getColorClass = (value: number) => {
    if (value <= 24) return 'text-red-500 bg-red-500/10 border-red-500/30';
    if (value <= 44) return 'text-orange-500 bg-orange-500/10 border-orange-500/30';
    if (value <= 55) return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/30';
    if (value <= 75) return 'text-green-500 bg-green-500/10 border-green-500/30';
    return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
  };

  // 計算指針角度 (0-100 映射到 -90 到 90 度)
  const angle = (data.value / 100) * 180 - 90;

  return (
    <div className={`card border-2 ${getColorClass(data.value)}`}>
      <div className="card-header border-b border-gray-800/50">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🌡️</span>
          <span>Crypto Fear & Greed Index</span>
        </div>
      </div>
      
      <div className="p-6">
        <div className="flex flex-col items-center">
          {/* 儀表盤視覺化 */}
          <div className="relative w-48 h-24 mb-4">
            {/* 背景半圓 */}
            <div className="absolute inset-0 flex justify-center">
              <div className="w-48 h-24 overflow-hidden">
                <div className="w-48 h-48 rounded-full border-8 border-gray-800"></div>
              </div>
            </div>
            
            {/* 顏色區段標記 */}
            <div className="absolute inset-0 flex justify-between items-end text-xs text-gray-500">
              <span className="text-red-500">Fear</span>
              <span className="text-yellow-500">Neutral</span>
              <span className="text-green-500">Greed</span>
            </div>
            
            {/* 指針 */}
            <div className="absolute inset-0 flex justify-center items-end">
              <div
                className="absolute bottom-0 w-1 h-20 bg-white origin-bottom transition-transform duration-500"
                style={{ transform: `rotate(${angle}deg)` }}
              >
                <div className="absolute -top-2 -left-1 w-3 h-3 bg-white rounded-full"></div>
              </div>
            </div>
          </div>

          {/* 數值與分類 */}
          <div className="text-center mb-4">
            <div className="text-6xl font-bold mb-2">{data.value}</div>
            <div className="text-xl font-semibold uppercase tracking-wider">
              {data.classification}
            </div>
          </div>

          {/* 描述 */}
          <div className="text-center text-sm text-gray-400 max-w-md">
            {data.description}
          </div>

          {/* 時間戳 */}
          <div className="mt-4 text-xs text-gray-500">
            Updated: {new Date(data.timestamp).toLocaleString()}
          </div>
        </div>
      </div>
    </div>
  );
}
