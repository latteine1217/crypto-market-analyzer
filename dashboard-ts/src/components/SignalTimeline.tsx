'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { format } from 'date-fns';
import { fetchSignals, MarketSignal } from '@/lib/api-client';

interface SignalTimelineProps {
  symbol?: string;
  limit?: number;
}

export const SignalTimeline: React.FC<SignalTimelineProps> = ({ symbol, limit = 50 }) => {
  const [signals, setSignals] = useState<MarketSignal[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastSignalTime, setLastSignalTime] = useState<number>(0);
  const [severityFilter, setSeverityFilter] = useState<'all' | 'critical' | 'warning' | 'info'>('all');

  // ✅ 使用 AudioContext 產生電子通知音 (避免外部資源依賴)
  const playAlertSound = (severity: string) => {
    try {
      const AudioContextClass = (window as any).AudioContext || (window as any).webkitAudioContext;
      if (!AudioContextClass) return;
      
      const ctx = new AudioContextClass();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = severity === 'critical' ? 'sawtooth' : 'sine';
      osc.frequency.setValueAtTime(severity === 'critical' ? 440 : 880, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(110, ctx.currentTime + 0.1);

      gain.gain.setValueAtTime(0.1, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.1);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start();
      osc.stop(ctx.currentTime + 0.1);
      setTimeout(() => {
        try {
          ctx.close();
        } catch (err) {
          console.error('Audio context close failed', err);
        }
      }, 200);
    } catch (e) {
      console.error('Audio alert failed', e);
    }
  };

  const loadSignals = async () => {
    try {
      const data = await fetchSignals(symbol, limit);
      
      // ✅ 檢查是否有新信號
      if (data.length > 0) {
        const latestTime = new Date(data[0].time).getTime();
        if (lastSignalTime !== 0 && latestTime > lastSignalTime) {
          // 僅對高嚴重級別信號播放聲音
          if (data[0].severity === 'critical' || data[0].severity === 'warning') {
            playAlertSound(data[0].severity);
          }
        }
        setLastSignalTime(latestTime);
      }
      
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
    const safeType = type || '';
    if (safeType.includes('divergence')) {
      return side === 'bullish' ? '📈' : '📉';
    }
    if (safeType === 'oi_spike') return '🔥';
    if (type === 'liquidation_cascade') return '💀';
    if (type === 'funding_extreme') return '💰';
    if (type === 'obi_extreme') return '⚖️';
    return '🔔';
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'border-red-500 bg-red-500/10 text-red-500';
      case 'warning': return 'border-amber-500 bg-amber-500/10 text-amber-500';
      default: return 'border-blue-500 bg-blue-500/10 text-blue-500';
    }
  };

  const severityCounts = useMemo(() => {
    const counts = { critical: 0, warning: 0, info: 0 };
    for (const signal of signals) {
      if (signal.severity === 'critical') counts.critical += 1;
      else if (signal.severity === 'warning') counts.warning += 1;
      else counts.info += 1;
    }
    return counts;
  }, [signals]);

  const filteredSignals = useMemo(() => {
    if (severityFilter === 'all') return signals;
    if (severityFilter === 'info') {
      return signals.filter((signal) => signal.severity !== 'critical' && signal.severity !== 'warning');
    }
    return signals.filter((signal) => signal.severity === severityFilter);
  }, [signals, severityFilter]);

  if (loading && signals.length === 0) {
    return <div className="p-4 text-gray-500">Loading signals...</div>;
  }

  return (
    <div className="card h-full flex flex-col overflow-hidden border border-gray-800 rounded-xl">
      <div className="px-4 py-3 border-b border-gray-800/90 flex justify-between items-center">
        <h3 className="text-[11px] font-bold tracking-wide text-gray-100 flex items-center gap-2 uppercase">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
          </span>
          Market Signals Timeline
        </h3>
        <button 
          onClick={loadSignals}
          className="text-[11px] font-medium text-gray-400 hover:text-white transition-colors"
        >
          Refresh
        </button>
      </div>

      <div className="px-4 py-3 border-b border-gray-800/70 flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-2 text-[10px]">
          <span className="px-2 py-0.5 rounded border border-red-500/30 text-red-400">Critical {severityCounts.critical}</span>
          <span className="px-2 py-0.5 rounded border border-amber-500/30 text-amber-400">Warning {severityCounts.warning}</span>
          <span className="px-2 py-0.5 rounded border border-blue-500/30 text-blue-400">Info {severityCounts.info}</span>
        </div>
        <div className="flex flex-wrap items-center gap-1">
          {(['all', 'critical', 'warning', 'info'] as const).map((key) => (
            <button
              key={key}
              onClick={() => setSeverityFilter(key)}
              className={`px-2 py-0.5 text-[10px] rounded border transition-colors ${
                severityFilter === key
                  ? 'border-gray-600 bg-gray-700/70 text-gray-100'
                  : 'border-gray-800 text-gray-500 hover:text-gray-300'
              }`}
            >
              {key.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2 custom-scrollbar">
        {filteredSignals.length === 0 ? (
          <div className="text-center py-10 text-gray-600 italic text-xs">
            {signals.length === 0 ? 'No signals detected recently' : 'No signals matched current filter'}
          </div>
        ) : (
          filteredSignals.map((signal, idx) => (
            <div key={idx} className="relative pl-4 pr-1 border-l border-gray-800 pb-1 group">
              {/* Dot */}
              <div className={`absolute -left-[4px] top-1.5 w-1.5 h-1.5 rounded-full ${
                signal.side === 'bullish' ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.5)]' : 
                signal.side === 'bearish' ? 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]' : 'bg-gray-500'
              }`} />
              
              <div className={`text-[11px] p-2 rounded border transition-all hover:bg-opacity-20 ${getSeverityColor(signal.severity)}`}>
                <div className="flex justify-between items-center mb-1">
                  <div className="font-bold flex items-center gap-1.5">
                    <span>{getSignalIcon(signal.signal_type, signal.side)}</span>
                    <span className="tracking-tighter">{(signal.signal_type || 'SIGNAL').replace(/_/g, ' ').toUpperCase()}</span>
                  </div>
                  <div className="text-[9px] font-mono opacity-60">
                    {format(new Date(signal.time), 'HH:mm:ss')}
                  </div>
                </div>
                
                <div className="text-gray-300 text-[10px] leading-tight mb-1 break-words">
                  <span className="text-blue-300 font-bold mr-1">#{signal.symbol}</span>
                  {signal.message}
                </div>
                
                {signal.price_at_signal && (
                  <div className="font-mono text-[9px] opacity-50 flex justify-end italic">
                    @{Number(signal.price_at_signal).toLocaleString()}
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
