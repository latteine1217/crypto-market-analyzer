'use client';

import React, { useEffect, useState } from 'react';
import { format } from 'date-fns';
import { fetchSignals, MarketSignal } from '@/lib/api-client';

interface SignalTimelineProps {
  symbol?: string;
  limit?: number;
}

export const SignalTimeline: React.FC<SignalTimelineProps> = ({ symbol, limit = 50 }) => {
  const [signals, setSignals] = useState<MarketSignal[]>([]);
  const [loading, setLoading] = useState(true);

  const loadSignals = async () => {
    try {
      // 這裡假設 api-client 有 fetchSignals 方法
      const data = await fetchSignals(symbol, limit);
      setSignals(data);
    } catch (error) {
      console.error('Failed to load signals', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSignals();
    const timer = setInterval(loadSignals, 30000); // 30s update
    return () => clearInterval(timer);
  }, [symbol, limit]);

  const getSignalIcon = (type: string, side: string) => {
    if (type.includes('divergence')) {
      return side === 'bullish' ? '📈' : '📉';
    }
    if (type === 'oi_spike') return '🔥';
    if (type === 'liquidation_cascade') return '💀';
    if (type === 'funding_extreme') return '💰';
    return '🔔';
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'border-red-500 bg-red-500/10 text-red-500';
      case 'warning': return 'border-amber-500 bg-amber-500/10 text-amber-500';
      default: return 'border-blue-500 bg-blue-500/10 text-blue-500';
    }
  };

  if (loading && signals.length === 0) {
    return <div className="p-4 text-gray-500">Loading signals...</div>;
  }

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 h-full flex flex-col">
      <div className="p-4 border-b border-gray-800 flex justify-between items-center">
        <h3 className="font-bold text-gray-100 flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
          </span>
          Market Signals Timeline
        </h3>
        <button 
          onClick={loadSignals}
          className="text-xs text-gray-400 hover:text-white transition-colors"
        >
          Refresh
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
        {signals.length === 0 ? (
          <div className="text-center py-10 text-gray-600 italic">No signals detected recently</div>
        ) : (
          signals.map((signal, idx) => (
            <div key={idx} className="relative pl-6 border-l border-gray-800 pb-2">
              {/* Dot */}
              <div className={`absolute -left-[5px] top-1 w-2.5 h-2.5 rounded-full border-2 ${
                signal.side === 'bullish' ? 'border-green-500 bg-green-900' : 
                signal.side === 'bearish' ? 'border-red-500 bg-red-900' : 'border-gray-500 bg-gray-900'
              }`} />
              
              <div className="text-[10px] text-gray-500 font-mono mb-1">
                {format(new Date(signal.time), 'HH:mm:ss')} • {signal.symbol}
              </div>
              
              <div className={`text-xs p-2 rounded border ${getSeverityColor(signal.severity)}`}>
                <div className="font-bold flex items-center gap-2 mb-1">
                  <span>{getSignalIcon(signal.signal_type, signal.side)}</span>
                  {signal.signal_type.replace(/_/g, ' ').toUpperCase()}
                </div>
                <div className="text-gray-300 leading-relaxed">
                  {signal.message}
                </div>
                {signal.price_at_signal && (
                  <div className="mt-1 font-mono text-[10px] opacity-70">
                    Price at Signal: ${Number(signal.price_at_signal).toLocaleString()}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
