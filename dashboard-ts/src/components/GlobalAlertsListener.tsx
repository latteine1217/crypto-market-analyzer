'use client'

import { useState, useEffect } from 'react'
import { io, Socket } from 'socket.io-client'
import { formatPrice } from '@/lib/utils'
import { useQueryClient } from '@tanstack/react-query'

interface ToastNotification {
  id: string;
  type: 'price_alert' | 'market_signal';
  title: string;
  message: string;
  time: Date;
  severity: 'info' | 'warning' | 'critical';
}

export function GlobalAlertsListener() {
  const [toasts, setToasts] = useState<ToastNotification[]>([])
  const queryClient = useQueryClient()

  useEffect(() => {
    // Connect to API Server
    const socketUrl = process.env.NEXT_PUBLIC_API_URL?.replace('/api', '') || 'http://localhost:8080';
    const socket: Socket = io(socketUrl, {
      transports: ['websocket'],
      reconnectionAttempts: 5
    });

    socket.on('connect', () => {
      console.log('WS Connected');
    });

    socket.on('price_alert', (data: any) => {
      addToast({
        id: Date.now().toString(),
        type: 'price_alert',
        title: `🔔 Price Alert: ${data.symbol}`,
        message: `${data.symbol} is ${data.condition} ${formatPrice(data.target_price)} (Triggered at ${formatPrice(data.trigger_price)})`,
        time: new Date(),
        severity: 'info'
      });
      // Refresh alert lists anywhere in the app
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    });

    socket.on('market_signal', (data: any) => {
      addToast({
        id: Date.now().toString() + Math.random(),
        type: 'market_signal',
        title: getSignalTitle(data.signal_type),
        message: `${data.message} (${data.symbol})`,
        time: new Date(),
        severity: data.severity || 'warning'
      });
    });

    return () => {
      socket.disconnect();
    };
  }, [queryClient]);

  const addToast = (toast: ToastNotification) => {
    setToasts(prev => [toast, ...prev].slice(0, 5)); // Keep max 5
    // Auto remove after 5s
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== toast.id));
    }, 5000);
  };

  const getSignalTitle = (type: string) => {
    switch(type) {
      case 'funding_extreme': return '⚠️ Extreme Funding Rate';
      case 'oi_spike': return '📊 Open Interest Spike';
      case 'cvd_divergence': return '📉 CVD Divergence';
      case 'liquidation_cascade': return '💧 Liquidation Cascade';
      default: return '📢 Market Signal';
    }
  };

  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-20 right-4 z-50 flex flex-col gap-2 w-80 pointer-events-none">
      {toasts.map(toast => (
        <div 
          key={toast.id} 
          className={`pointer-events-auto p-4 rounded shadow-lg border-l-4 animate-slide-in backdrop-blur-md bg-opacity-90 transition-all duration-300 ${
            toast.severity === 'critical' ? 'bg-red-900/90 border-red-500 text-white' :
            toast.severity === 'warning' ? 'bg-yellow-900/90 border-yellow-500 text-yellow-100' :
            'bg-blue-900/90 border-blue-500 text-blue-100'
          }`}
        >
          <div className="flex justify-between items-start">
            <h4 className="font-bold text-sm">{toast.title}</h4>
            <span className="text-[10px] opacity-70">{toast.time.toLocaleTimeString()}</span>
          </div>
          <p className="text-sm mt-1">{toast.message}</p>
        </div>
      ))}
    </div>
  )
}
