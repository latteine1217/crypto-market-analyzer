'use client'

import { useQuery } from '@tanstack/react-query'
import { fetchRichList } from '@/lib/api-client'
import { RichListTable } from '@/components/RichListTable'

export default function OnChainPage() {
  const { data: richList, isLoading } = useQuery({
    queryKey: ['richList', 'BTC'],
    queryFn: () => fetchRichList('BTC', 30),
    refetchInterval: 1000 * 60 * 60, // Refresh every hour
  })

  // 簡單判斷：如果數據量太少（例如剛初始化），啟用 demo 模式展示 UI
  // 在實際生產環境中，應移除 demoMode 或僅在開發環境啟用
  const showDemo = !isLoading && (!richList || richList.length < 24); // 假設一天至少有幾筆數據，或者根據日期數判斷

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">On-Chain Analysis</h1>
        <p className="text-gray-400">Blockchain network statistics and whale tracking</p>
      </div>

      <div className="grid grid-cols-1 gap-6">
        <div className="card overflow-hidden">
          <div className="p-6 pb-0">
            <h2 className="card-header">Bitcoin Rich List Changes</h2>
            <p className="text-sm text-gray-500 mb-6">
              Daily balance changes across different address tiers. 
              {showDemo && <span className="text-yellow-500 ml-2">(Displaying Demo Data - Insufficient History)</span>}
            </p>
          </div>
          
          <div className="w-full">
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
              <RichListTable data={richList || []} demoMode={showDemo} />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
