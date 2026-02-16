'use client'

import { useQuery } from '@tanstack/react-query'
import { fetchRichList } from '@/lib/api-client'
import { RichListTable } from '@/components/RichListTable'
import { WhaleRadar } from '@/components/WhaleRadar'
import { WhaleDistributionChart } from '@/components/charts/WhaleDistributionChart'
import { QUERY_PROFILES } from '@/lib/queryProfiles'

export default function OnChainPage() {
  const { data: richList, isLoading } = useQuery({
    queryKey: ['richList', 'BTC'],
    queryFn: () => fetchRichList('BTC', 30),
    ...QUERY_PROFILES.hourly,
  })

  return (
    <div className="max-w-[1600px] mx-auto space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black tracking-tighter mb-1">ON-CHAIN INTELLIGENCE</h1>
          <p className="text-sm text-gray-500 font-medium italic">Monitoring address distribution and high-value movements</p>
        </div>
        <div className="flex items-center gap-2 bg-[#1e2329] px-4 py-2 rounded-lg border border-gray-800">
          <span className="text-xs font-bold text-blue-400">NETWORK: BTC</span>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        {/* Left: Radar & Stats */}
        <div className="xl:col-span-1 space-y-6">
          <div className="h-[700px]">
            <WhaleRadar />
          </div>
          <div className="card p-4">
            <h3 className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-3">Network Pulse</h3>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-xs text-gray-400">Active Addresses</span>
                <span className="text-sm font-mono font-bold text-white">942,051</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs text-gray-400">Hash Rate</span>
                <span className="text-sm font-mono font-bold text-white">612 EH/s</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs text-gray-400">Next Halving</span>
                <span className="text-sm font-mono font-bold text-blue-400">~15 Days</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Distribution Charts & Tables */}
        <div className="xl:col-span-3 space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="card h-[400px]">
              <h2 className="card-header border-none mb-0">BTC HOLDING DISTRIBUTION</h2>
              <WhaleDistributionChart symbol="BTC" />
            </div>
            <div className="card h-[400px] flex flex-col justify-center p-6 bg-gradient-to-br from-[#1e2329] to-[#0b0e11]">
               <div className="text-center">
                  <span className="text-[10px] font-black text-blue-500 uppercase tracking-widest mb-2 block">Dormant Supply</span>
                  <div className="text-5xl font-black text-white mb-2">68.4%</div>
                  <p className="text-xs text-gray-500 max-w-[250px] mx-auto">
                    Supply last moved {'>'} 1 year ago. Indicating high conviction from long-term holders.
                  </p>
               </div>
            </div>
          </div>

          <div className="card overflow-hidden">
            <div className="p-6 border-b border-gray-800 flex justify-between items-center">
              <div>
                <h2 className="text-lg font-bold">ADDRESS TIER CHANGES</h2>
                <p className="text-xs text-gray-500">Daily balance trends across wallet sizes</p>
              </div>
              <span className="text-[10px] font-mono text-gray-600 uppercase">30D LOOKBACK</span>
            </div>
            
            <div className="w-full overflow-x-auto custom-scrollbar">
              {isLoading ? (
                <div className="space-y-4 p-6 animate-pulse">
                  <div className="h-10 bg-gray-800 rounded"></div>
                  <div className="space-y-2">
                    {[...Array(10)].map((_, i) => (
                      <div key={i} className="h-8 bg-gray-800/50 rounded"></div>
                    ))}
                  </div>
                </div>
              ) : (
                <RichListTable data={richList || []} />
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
