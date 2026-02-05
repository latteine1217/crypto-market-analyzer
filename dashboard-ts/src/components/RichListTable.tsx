'use client'

import { useMemo } from 'react'
import { clsx } from 'clsx'
import { formatNumber } from '@/lib/utils'
import type { RichListStat } from '@/types/market'

interface Props {
  data: RichListStat[]
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
    // --- 準備數據源 ---
    let sourceData = data || []

    if (sourceData.length === 0) {
      return { dates: [], rows: [] }
    }

    // --- 真實數據處理邏輯 ---
    
    const parseRange = (rawGroup: string) => {
      const cleaned = rawGroup.replace(/[\[\]\(\)]/g, '').replace(/,/g, '').trim()
      if (!cleaned) return null
      if (cleaned.includes('-')) {
        const parts = cleaned.split('-').map(p => p.trim())
        const min = parseFloat(parts[0])
        const max = parseFloat(parts[1])
        if (Number.isFinite(min) && Number.isFinite(max)) return { min, max }
      }
      if (cleaned.includes('+')) {
        const min = parseFloat(cleaned.replace('+', '').trim())
        if (Number.isFinite(min)) return { min, max: Infinity }
      }
      return null
    }

    const isExactTier = (range: { min: number; max: number }, tier: { min: number; max: number }) => {
      if (tier.max === Infinity) return range.min === tier.min && range.max === Infinity
      return range.min === tier.min && range.max === tier.max
    }

    // 1. 按日期分組（使用 UTC 日期，避免時區導致重複）
    const groupedByDate: Record<string, RichListStat[]> = {}
    sourceData.forEach(d => {
      if (!d || !d.snapshot_date) return
      const dateStr = new Date(d.snapshot_date).toISOString().split('T')[0]
      if (!groupedByDate[dateStr]) groupedByDate[dateStr] = []
      groupedByDate[dateStr].push(d)
    })

    // 排序日期 (新到舊)
    const sortedDates = Object.keys(groupedByDate).sort((a, b) => new Date(b).getTime() - new Date(a).getTime())
    
    // 取最近 5 天
    const displayDates = sortedDates.slice(0, 5)
    
    // 格式化日期標頭 (e.g., 1/14)
    const dateHeaders = displayDates.map(d => 
      new Date(d).toLocaleDateString('en-US', { month: 'numeric', day: 'numeric' })
    )

    // 2. 聚合層級數據
    const rows = TARGET_TIERS.map(tier => {
      const dailyBalances = displayDates.map(date => {
        const dayStats = groupedByDate[date] || []

        // 去重：同一天同一 range 只取最新一筆
        const latestByRange = new Map<string, RichListStat>()
        dayStats.forEach(stat => {
          const key = stat.rank_group || ''
          const existing = latestByRange.get(key)
          if (!existing) {
            latestByRange.set(key, stat)
            return
          }
          const existingTime = new Date(existing.snapshot_date).getTime()
          const currentTime = new Date(stat.snapshot_date).getTime()
          if (currentTime > existingTime) {
            latestByRange.set(key, stat)
          }
        })

        const normalizedStats = Array.from(latestByRange.values())

        // 若存在精確區間，直接使用（避免重複加總子區間）
        const exactRow = normalizedStats.find(stat => {
          const range = parseRange(stat.rank_group || '')
          return range ? isExactTier(range, tier) : false
        })
        if (exactRow) return Number(exactRow.total_balance)

        // 否則聚合子區間（完全落在該 tier 範圍內）
        const total = normalizedStats.reduce((sum, stat) => {
          const range = parseRange(stat.rank_group || '')
          if (!range) return sum
          const within = range.min >= tier.min && (tier.max === Infinity || range.max <= tier.max)
          if (within) return sum + Number(stat.total_balance)
          return sum
        }, 0)

        return total
      })

      // 3. 計算變化量
      const changes = dailyBalances.map((balance, i) => {
        if (i === dailyBalances.length - 1) return 0 
        const prevBalance = dailyBalances[i + 1]
        if (balance === 0 || prevBalance === 0) return 0
        return balance - prevBalance
      })

      return {
        tier: tier.label,
        totalHeld: dailyBalances[0], 
        changes: changes.slice(0, -1) // 最後一個日期無法計算變化
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
