'use client'

import { useState, useMemo, memo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { 
  fetchOHLCV, 
  fetchMarkets, 
  fetchFundingRate, 
  fetchOpenInterest 
} from '@/lib/api-client'
import { calculateAllIndicators } from '@/lib/indicators'
import { LightweightCandlestickChart } from '@/components/charts/LightweightCandlestickChart'
import { MACDChart } from '@/components/charts/MACDChart'
import { FundingRateChart } from '@/components/charts/FundingRateChart'
import { OpenInterestChart } from '@/components/charts/OpenInterestChart'
import { IndicatorStats } from '@/components/IndicatorStats'
import { AlertsManager } from '@/components/AlertsManager'

// Memoize components to prevent re-renders when visibility toggles
const MemoizedMACDChart = memo(MACDChart)
const MemoizedFundingRateChart = memo(FundingRateChart)
const MemoizedOpenInterestChart = memo(OpenInterestChart)
const MemoizedIndicatorStats = memo(IndicatorStats)
const MemoizedLightweightCandlestickChart = memo(LightweightCandlestickChart)

export default function TechnicalPage() {
  const [exchange, setExchange] = useState('binance')
  const [symbol, setSymbol] = useState('BTCUSDT')
  const [timeframe, setTimeframe] = useState('1m')

  // 指標可見性狀態
  const [visibleIndicators, setVisibleIndicators] = useState({
    ma20: true,
    ma60: true,
    ma200: true,
    bb: false,   // 布林帶預設關閉
    macd: true,
  })

  const { data: markets } = useQuery({
    queryKey: ['markets'],
    queryFn: fetchMarkets,
  })

  const { data: ohlcv, isLoading } = useQuery({
    queryKey: ['ohlcv', exchange, symbol, timeframe],
    queryFn: () => fetchOHLCV(exchange, symbol, { limit: 500, timeframe }),
    refetchInterval: 15000,
  })

  const { data: fundingRate } = useQuery({
    queryKey: ['funding-rate', exchange, symbol],
    queryFn: () => fetchFundingRate(exchange, symbol, 100),
    refetchInterval: 30000,
    enabled: ['binance', 'bybit', 'okx'].includes(exchange),
  })

  const { data: openInterest } = useQuery({
    queryKey: ['open-interest', exchange, symbol],
    queryFn: () => fetchOpenInterest(exchange, symbol, 100),
    refetchInterval: 30000,
    enabled: ['binance', 'bybit', 'okx'].includes(exchange),
  })

  const dataWithIndicators = useMemo(() => {
    if (!ohlcv || ohlcv.length === 0) return null
    // 只計算最近 300 條
    const recentData = ohlcv.length > 300 ? ohlcv.slice(-300) : ohlcv
    return calculateAllIndicators(recentData)
  }, [ohlcv])

  const filteredMarkets = markets?.filter(m => m.exchange === exchange)

  const toggleIndicator = (key: keyof typeof visibleIndicators) => {
    setVisibleIndicators(prev => ({ ...prev, [key]: !prev[key] }))
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold mb-2">Technical Analysis</h1>
          <p className="text-gray-400">Candlestick charts with technical indicators & derivatives data</p>
        </div>

        <div className="flex flex-wrap gap-4">
          <select
            value={exchange}
            onChange={(e) => setExchange(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded px-4 py-2"
          >
            <option value="binance">Binance</option>
            <option value="bybit">Bybit</option>
            <option value="okx">OKX</option>
          </select>

          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded px-4 py-2 min-w-[150px]"
          >
            {filteredMarkets?.map(m => (
              <option key={m.id} value={m.symbol}>
                {m.symbol}
              </option>
            ))}
          </select>

          <div className="flex bg-gray-800 rounded p-1 border border-gray-700">
            {['1m', '5m', '15m', '1h', '4h', '1d'].map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-3 py-1 text-sm rounded transition-colors ${
                  timeframe === tf
                    ? 'bg-primary text-white font-medium'
                    : 'text-gray-400 hover:text-white hover:bg-gray-700'
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>
      </div>

      {isLoading && (
        <div className="space-y-6 animate-pulse">
          <div className="h-64 bg-gray-800/50 rounded-xl border border-gray-700 flex items-center justify-center">
            <div className="flex flex-col items-center">
              <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-4"></div>
              <p className="text-gray-400">Fetching market data...</p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="h-48 bg-gray-800/50 rounded-xl border border-gray-700"></div>
            <div className="h-48 bg-gray-800/50 rounded-xl border border-gray-700"></div>
          </div>
        </div>
      )}

      {dataWithIndicators && (
        <>
          {/* 指標控制面板 */}
          <div className="flex flex-wrap gap-2 items-center bg-gray-900/50 p-2 rounded-lg border border-gray-800">
            <span className="text-sm text-gray-400 mr-2 px-2">Indicators:</span>
            
            <label className="flex items-center space-x-2 px-3 py-1 bg-gray-800 rounded cursor-pointer hover:bg-gray-700 transition-colors">
              <input 
                type="checkbox" 
                checked={visibleIndicators.ma20} 
                onChange={() => toggleIndicator('ma20')}
                className="rounded border-gray-600 text-blue-500 focus:ring-blue-500 bg-gray-700"
              />
              <span className="text-sm text-blue-400">MA 20</span>
            </label>

            <label className="flex items-center space-x-2 px-3 py-1 bg-gray-800 rounded cursor-pointer hover:bg-gray-700 transition-colors">
              <input 
                type="checkbox" 
                checked={visibleIndicators.ma60} 
                onChange={() => toggleIndicator('ma60')}
                className="rounded border-gray-600 text-amber-500 focus:ring-amber-500 bg-gray-700"
              />
              <span className="text-sm text-amber-500">MA 60</span>
            </label>

            <label className="flex items-center space-x-2 px-3 py-1 bg-gray-800 rounded cursor-pointer hover:bg-gray-700 transition-colors">
              <input 
                type="checkbox" 
                checked={visibleIndicators.ma200} 
                onChange={() => toggleIndicator('ma200')}
                className="rounded border-gray-600 text-purple-500 focus:ring-purple-500 bg-gray-700"
              />
              <span className="text-sm text-purple-500">MA 200</span>
            </label>

            <label className="flex items-center space-x-2 px-3 py-1 bg-gray-800 rounded cursor-pointer hover:bg-gray-700 transition-colors">
              <input 
                type="checkbox" 
                checked={visibleIndicators.bb} 
                onChange={() => toggleIndicator('bb')}
                className="rounded border-gray-600 text-cyan-500 focus:ring-cyan-500 bg-gray-700"
              />
              <span className="text-sm text-cyan-400">Bollinger Bands</span>
            </label>
            
            <label className="flex items-center space-x-2 px-3 py-1 bg-gray-800 rounded cursor-pointer hover:bg-gray-700 transition-colors">
              <input 
                type="checkbox" 
                checked={visibleIndicators.macd} 
                onChange={() => toggleIndicator('macd')}
                className="rounded border-gray-600 text-gray-400 focus:ring-gray-500 bg-gray-700"
              />
              <span className="text-sm text-gray-300">MACD</span>
            </label>
          </div>

          {/* K 線圖與移動平均 */}
          <div className="card">
            <h2 className="card-header">Candlestick Chart</h2>
            <MemoizedLightweightCandlestickChart 
              data={dataWithIndicators} 
              visibleIndicators={visibleIndicators}
            />
          </div>

          {/* MACD 指標 (可選顯示) */}
          {visibleIndicators.macd && (
            <div className="card">
              <h2 className="card-header">MACD Indicator</h2>
              <MemoizedMACDChart data={dataWithIndicators} />
            </div>
          )}

          {/* 資金費率 */}
          {fundingRate && fundingRate.length > 0 && (
            <div className="card">
              <h2 className="card-header">Funding Rate (Perpetual)</h2>
              <MemoizedFundingRateChart data={fundingRate} />
            </div>
          )}

          {/* 持倉量 */}
          {openInterest && openInterest.length > 0 && (
            <div className="card">
              <h2 className="card-header">Open Interest</h2>
              <MemoizedOpenInterestChart data={openInterest} />
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="md:col-span-1">
              <AlertsManager 
                currentSymbol={symbol} 
                currentPrice={dataWithIndicators[dataWithIndicators.length - 1]?.close} 
              />
            </div>

            <div className="md:col-span-2 card">
              <h2 className="card-header">Technical Indicators</h2>
              <MemoizedIndicatorStats data={dataWithIndicators} />
            </div>
          </div>
        </>
      )}
    </div>
  )
}