'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchSystemStatus } from '@/lib/api-client';
import { DataQualityStatus } from '@/components/DataQualityStatus';

export default function StatusPage() {
  const { data: status, isLoading, error } = useQuery({
    queryKey: ['systemStatus'],
    queryFn: fetchSystemStatus,
    refetchInterval: 10000, // 每 10 秒刷新一次
  });

  const getStatusColor = (s?: string) => {
    switch (s) {
      case 'operational': return 'text-success';
      case 'degraded': return 'text-warning';
      case 'error': return 'text-danger';
      default: return 'text-gray-500';
    }
  };

  const getActiveCollectors = () => status?.collectors?.filter(c => c.is_active).length || 0;

  if (error) {
    return (
      <div className="p-12 text-center card border-danger/20 bg-danger/5">
        <div className="text-danger font-bold mb-2">⚠️ System Status Unreachable</div>
        <p className="text-sm text-gray-500">Failed to communicate with API server. Please check infrastructure health.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div>
          <h1 className="text-4xl font-bold mb-2 bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-500">
            System Status
          </h1>
          <p className="text-gray-400">Real-time infrastructure health monitoring</p>
        </div>
        {status?.timestamp && (
          <div className="text-[10px] font-mono text-gray-500">
            LAST SYNC: {new Date(status.timestamp).toLocaleTimeString()}
          </div>
        )}
      </div>

      {/* Network Status Card */}
      <div className="card border-gray-800/50">
        <h2 className="card-header flex items-center gap-2 border-b border-gray-800/50">
          <span className={`w-2 h-2 rounded-full ${isLoading ? 'bg-gray-600' : 'bg-success animate-pulse'}`}></span>
          <span>System Infrastructure Health</span>
        </h2>
        
        <div className="p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* API Server Status */}
          <div className="space-y-2">
            <div className="text-[10px] uppercase tracking-widest text-gray-500 font-medium">API Server</div>
            <div className="flex items-center gap-2">
              <span className={`text-xl font-bold ${getStatusColor(status?.services?.api_server?.status)}`}>
                {status?.services?.api_server?.status?.toUpperCase() || 'CHECKING...'}
              </span>
            </div>
            <p className="text-xs text-gray-500">Latency: {status?.services?.api_server?.api_latency_ms || 0}ms</p>
          </div>

          {/* Database Status */}
          <div className="space-y-2">
            <div className="text-[10px] uppercase tracking-widest text-gray-500 font-medium">Database (Timescale)</div>
            <div className="text-xl font-bold text-gray-200">
              {status?.services?.database?.status?.toUpperCase() || '...'}
            </div>
            <p className="text-xs text-gray-500">Size: {status?.services?.database?.db_size || '-'}</p>
          </div>

          {/* Active Collectors */}
          <div className="space-y-2">
            <div className="text-[10px] uppercase tracking-widest text-gray-500 font-medium">Active Collectors</div>
            <div className="text-xl font-bold text-gray-200">
              {getActiveCollectors()} / {status?.collectors?.length || 0}
            </div>
            <p className="text-xs text-gray-500">Node: Bybit Dedicated</p>
          </div>

          {/* Redis Status */}
          <div className="space-y-2">
            <div className="text-[10px] uppercase tracking-widest text-gray-500 font-medium">Cache (Redis)</div>
            <div className="text-xl font-bold text-success">
              {status?.services?.redis?.status?.toUpperCase() || '...'}
            </div>
            <p className="text-xs text-gray-500">Memory: {status?.services?.redis?.memory_used || '-'}</p>
          </div>
        </div>

        {/* Live Collectors Grid */}
        <div className="mx-6 mb-6">
          <h4 className="text-[10px] font-bold text-gray-500 mb-3 tracking-widest uppercase">REAL-TIME DATA INGESTION NODES</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {status?.collectors?.map((c) => (
              <div key={`${c.exchange}-${c.symbol}`} className="p-4 bg-gray-900/50 border border-gray-800 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-gray-200">{c.exchange.toUpperCase()}</span>
                    <span className="text-[10px] text-gray-500">/</span>
                    <span className="text-xs font-mono text-primary">{c.symbol}</span>
                  </div>
                  <span className={`h-2 w-2 rounded-full ${c.is_active ? 'bg-success animate-pulse' : 'bg-danger'}`}></span>
                </div>
                <div className="flex justify-between items-center text-[10px]">
                  <span className="text-gray-500 uppercase tracking-tighter">Last Data Point</span>
                  <span className="text-gray-400 font-mono">
                    {c.last_data_time ? new Date(c.last_data_time).toLocaleTimeString() : 'N/A'}
                  </span>
                </div>
              </div>
            ))}
            {(!status?.collectors || status.collectors.length === 0) && !isLoading && (
              <div className="col-span-2 p-8 text-center text-gray-600 border border-dashed border-gray-800 rounded-lg">
                No active data collection nodes detected
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Database Performance Card */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card border-gray-800/50 p-5 bg-gradient-to-br from-gray-900 to-black">
          <div className="text-xs text-gray-500 uppercase tracking-widest mb-1">Total Time-series Records</div>
          <div className="text-3xl font-bold text-gray-100">
            {status?.services?.database?.total_records?.toLocaleString() || '0'}
          </div>
          <div className="mt-2 h-1 w-full bg-gray-800 rounded-full overflow-hidden">
            <div className="h-full bg-primary animate-progress" style={{ width: '70%' }}></div>
          </div>
        </div>
        
        <div className="card border-gray-800/50 p-5">
          <div className="text-xs text-gray-500 uppercase tracking-widest mb-1">Cache Uptime</div>
          <div className="text-3xl font-bold text-success">
            {status?.services?.redis?.uptime ? Math.floor(status.services.redis.uptime / 3600) : 0} <span className="text-sm font-normal text-gray-500">hours</span>
          </div>
        </div>

        <div className="card border-gray-800/50 p-5">
          <div className="text-xs text-gray-500 uppercase tracking-widest mb-1">Environment</div>
          <div className="text-3xl font-bold text-indigo-400 capitalize">
            {status?.services?.api_server?.env || 'PRODUCTION'}
          </div>
        </div>
      </div>

      {/* Data Quality Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-indigo-400">Data Quality Metrics</h2>
            <p className="text-sm text-gray-500 mt-1">Real-time monitoring of OHLCV data completeness</p>
          </div>
        </div>
        <DataQualityStatus />
      </div>
    </div>
  );
}
