'use client'

import { useMemo } from 'react'
import { clsx } from 'clsx'
import { formatNumber } from '@/lib/utils'
import type { RichListStat } from '@/types/market'

interface Props {
  data: RichListStat[]
  demoMode?: boolean // 如果為 true，使用演示數據展示 UI 效果
}

// 定義目標層級
const TARGET_TIERS = [
  { id: '0-1', label: '(0-1) Coins', min: 0, max: 1 },
  { id: '1-10', label: '(1-10) Coins', min: 1, max: 10 },
  { id: '10-100', label: '(10-100) Coins', min: 10, max: 100 },
  { id: '100+', label: '(100+) Coins', min: 100, max: Infinity },
]

export function RichListTable({ data }: Props) {
  // 處理數據邏輯
  const processedData = useMemo(() => {
    // 檢查資料是否足夠
    if (!data || data.length === 0) {
      return { dates: [], rows: [] }
    }

    // --- 真實數據處理邏輯 ---
    
    // 1. 按日期分組
    const groupedByDate: Record<string, RichListStat[]> = {}
    data.forEach(d => {
      // 忽略時間，只看日期
      const dateStr = new Date(d.snapshot_date).toLocaleDateString()
      if (!groupedByDate[dateStr]) groupedByDate[dateStr] = []
      groupedByDate[dateStr].push(d)
    })

    // 排序日期 (新到舊)
    const sortedDates = Object.keys(groupedByDate).sort((a, b) => new Date(b).getTime() - new Date(a).getTime())
    
    // 取最近 5 天，如果數據不足則取所有可用天數
    // 最少需要 2 天才能計算變化
    const displayDates = sortedDates.slice(0, Math.min(5, sortedDates.length))
    
    // 格式化日期標頭 (e.g., 1/14)
    const dateHeaders = displayDates.map(d => 
      new Date(d).toLocaleDateString('en-US', { month: 'numeric', day: 'numeric' })
    )

    // 2. 聚合層級數據
    const rows = TARGET_TIERS.map(tier => {
      // 計算每一天的該層級總量
      const dailyBalances = displayDates.map(date => {
        const dayStats = groupedByDate[date] || []
        
        // 篩選屬於該層級的 stats 並加總
        const total = dayStats.reduce((sum, stat) => {
          // 解析 rank_group (e.g. "[100 - 1,000)" or "(0 - 0.00001)")
          // 移除逗號，提取第一個數字作為範圍下限
          const clean = stat.rank_group.replace(/,/g, '')
          
          // 匹配開頭的數字（整數或小數）
          // 例如: "[100 - 1000)" -> 100, "(0 - 0.00001)" -> 0, "[1000 - 10000)" -> 1000
          const match = clean.match(/^[\(\[](\d+(?:\.\d+)?)\s*-/)
          const rangeMin = match ? parseFloat(match[1]) : 0
          
          // 判斷是否屬於當前目標層級
          if (rangeMin >= tier.min && (tier.max === Infinity || rangeMin < tier.max)) {
            return sum + Number(stat.total_balance)
          }
          return sum
        }, 0)
        
        return total
      })

      // 3. 計算變化量 (Diff)
      // changes[0] = Day0 - Day1
      // changes[1] = Day1 - Day2 ...
      const changes = dailyBalances.map((balance, i) => {
        // 最後一天沒有前一天可對比，或者如果沒有上一筆數據
        if (i === dailyBalances.length - 1) return 0 
        const prevBalance = dailyBalances[i + 1]
        // 如果數據不完整 (0)，則無變化
        if (balance === 0 || prevBalance === 0) return 0
        
        return balance - prevBalance
      })
      
      // 移除最後一個 "0" (因為它是最舊的一天，無法計算變化，表格上我們通常不顯示最舊那一天的變化，或者只顯示 N-1 個變化欄位)
      // 但根據圖片，日期欄位下方顯示的是「該日相對於昨日」的變化。
      // 所以如果顯示 5 個日期，最後一個日期 (最舊) 通常無法顯示變化，除非我們抓了 6 天的資料。
      // 這裡簡單處理：顯示 0

      return {
        tier: tier.label,
        totalHeld: dailyBalances[0], // 最新總持倉
        changes: changes
      }
    })

    return {
      dates: dateHeaders,
      rows
    }

  }, [data])

  if (processedData.rows.length === 0) {
    return (
      <div className="card border-gray-800/50 bg-gray-900/20 p-12 flex flex-col items-center justify-center text-center">
        <div className="w-16 h-16 bg-gray-800 rounded-full flex items-center justify-center mb-4">
          <span className="text-2xl">📊</span>
        </div>
        <h3 className="text-lg font-bold text-gray-300 mb-2">Insufficient History Data</h3>
        <p className="text-gray-500 max-w-md">
          Rich list data is collected daily. Please wait for the next scheduled update or run a backfill to see historical changes.
        </p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse">
        <thead>
          <tr>
            <th className="p-4 text-left font-bold text-gray-200 border-b border-gray-700 w-48">
              BTC Address Tiers
            </th>
            <th className="p-4 text-right font-bold text-gray-200 border-b border-gray-700 w-40">
              BTC held
            </th>
            {processedData.dates.map((date, i) => (
              <th key={i} className="p-4 text-center font-bold text-gray-200 border-b border-gray-700 w-32">
                {date}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {processedData.rows.map((row, rowIdx) => (
            <tr key={row.tier} className="border-b border-gray-800 hover:bg-gray-800/30 transition-colors">
              {/* 層級名稱 */}
              <td className="p-4 text-left font-bold text-gray-300">
                {row.tier}
              </td>
              
              {/* 總持倉量 */}
              <td className="p-4 text-right font-bold text-gray-200">
                {formatNumber(row.totalHeld, 0)}
              </td>
              
              {/* 每日變化 */}
              {row.changes.map((change, colIdx) => {
                const isPositive = change > 0
                const isNegative = change < 0
                const isZero = change === 0
                
                return (
                  <td key={colIdx} className="p-1">
                    <div className={clsx(
                      "flex items-center justify-center h-12 rounded font-bold text-sm",
                      isPositive && "bg-green-600 text-white",
                      isNegative && "bg-red-600 text-white",
                      isZero && "bg-gray-800/50 text-gray-500"
                    )}>
                      {isPositive ? '+' : ''}
                      {formatNumber(change, 0)} BTC
                    </div>
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
