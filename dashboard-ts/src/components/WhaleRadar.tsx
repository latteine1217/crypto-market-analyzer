'use client';

import React, { useEffect, useState } from 'react';
import { format } from 'date-fns';
import { fetchWhaleTransactions, WhaleTransaction } from '@/lib/api-client';

export const WhaleRadar: React.FC = () => {
  const [transactions, setTransactions] = useState<WhaleTransaction[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      const data = await fetchWhaleTransactions(20);
      setTransactions(data);
    } catch (error) {
      console.error('Failed to fetch whale transactions', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const timer = setInterval(loadData, 60000); // 每分鐘更新一次
    return () => clearInterval(timer);
  }, []);

  const formatAddr = (addr: string) => {
    if (!addr || addr === 'unknown') return 'Unknown Wallet';
    return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
  };

  return (
    <div className="card flex flex-col h-full overflow-hidden border-blue-500/20 shadow-blue-900/10">
      <div className="p-4 border-b border-gray-800 flex justify-between items-center bg-blue-500/5">
        <div className="flex items-center gap-3">
          <div className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-blue-500"></span>
          </div>
          <h2 className="text-sm font-black tracking-widest uppercase">WHALE RADAR</h2>
        </div>
        <span className="text-[10px] font-mono text-gray-500 tracking-tighter">THRESHOLD: &gt;$1.0M</span>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-2">
        {loading && transactions.length === 0 ? (
          <div className="flex items-center justify-center h-40 text-gray-600 animate-pulse text-xs font-bold uppercase tracking-widest">
            Scanning blocks...
          </div>
        ) : (
          transactions.map((tx, idx) => (
            <div 
              key={tx.tx_hash} 
              className="p-3 rounded-lg bg-[#1e2329]/50 border border-gray-800/50 hover:border-blue-500/30 transition-all group relative overflow-hidden"
              style={{ animationDelay: `${idx * 100}ms` }}
            >
              {/* Radar pulse effect background */}
              <div className="absolute inset-0 bg-blue-500/5 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-1000 ease-in-out"></div>
              
              <div className="flex justify-between items-start mb-2 relative z-10">
                <div className="flex items-center gap-2">
                  <span className="bg-orange-500/20 text-orange-500 text-[9px] font-black px-1.5 py-0.5 rounded border border-orange-500/20 uppercase tracking-widest">
                    {tx.blockchain}
                  </span>
                  <span className="text-xs font-mono font-bold text-gray-400">
                    {format(new Date(tx.timestamp), 'HH:mm:ss')}
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-sm font-black text-blue-400 font-mono">
                    ${(tx.amount_usd / 1000000).toFixed(2)}M
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between text-[10px] relative z-10">
                <div className="flex flex-col">
                  <span className="text-gray-500 font-bold uppercase tracking-tighter mb-0.5">From</span>
                  <span className="text-gray-300 font-mono bg-black/30 px-1.5 py-0.5 rounded border border-gray-800">
                    {formatAddr(tx.from_addr)}
                  </span>
                </div>
                <div className="px-2 text-gray-700">→</div>
                <div className="flex flex-col items-end">
                  <span className="text-gray-500 font-bold uppercase tracking-tighter mb-0.5">To</span>
                  <span className="text-gray-300 font-mono bg-black/30 px-1.5 py-0.5 rounded border border-gray-800">
                    {formatAddr(tx.to_addr)}
                  </span>
                </div>
              </div>

              <div className="mt-2 pt-2 border-t border-gray-800/50 flex justify-between items-center relative z-10">
                <a 
                  href={`https://mempool.space/tx/${tx.tx_hash}`} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-[9px] text-gray-600 hover:text-blue-400 font-mono transition-colors"
                >
                  TX: {tx.tx_hash.slice(0, 12)}...
                </a>
                <span className="text-[9px] font-black text-green-500/50 uppercase tracking-widest">Verified</span>
              </div>
            </div>
          ))
        )}
      </div>
      
      <div className="p-3 bg-black/20 border-t border-gray-800 flex justify-center">
         <div className="text-[10px] text-gray-600 font-bold uppercase tracking-widest flex items-center gap-2">
            <span className="w-1 h-1 rounded-full bg-blue-500"></span>
            Live On-chain Feed Active
         </div>
      </div>
    </div>
  );
};
