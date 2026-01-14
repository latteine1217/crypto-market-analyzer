import Link from 'next/link'

export default function HomePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-4xl font-bold mb-2">Crypto Market Dashboard</h1>
        <p className="text-gray-400">Real-time cryptocurrency market analysis and monitoring</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Link href="/overview" className="card hover:border-primary transition-colors">
          <h2 className="text-xl font-semibold mb-2">📊 Market Overview</h2>
          <p className="text-gray-400">View latest prices and 24h changes across all markets</p>
        </Link>

        <Link href="/technical" className="card hover:border-primary transition-colors">
          <h2 className="text-xl font-semibold mb-2">📈 Technical Analysis</h2>
          <p className="text-gray-400">Candlestick charts with technical indicators (MACD, MA, RSI)</p>
        </Link>

        <Link href="/liquidity" className="card hover:border-primary transition-colors">
          <h2 className="text-xl font-semibold mb-2">💧 Liquidity Analysis</h2>
          <p className="text-gray-400">Order book depth and liquidity heatmaps</p>
        </Link>
      </div>

      <div className="card">
        <h3 className="card-header">System Status</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <div className="stat-label">Data Collection</div>
            <div className="stat-value text-success">Active</div>
          </div>
          <div>
            <div className="stat-label">Markets</div>
            <div className="stat-value">11</div>
          </div>
          <div>
            <div className="stat-label">Exchanges</div>
            <div className="stat-value">3</div>
          </div>
          <div>
            <div className="stat-label">Uptime</div>
            <div className="stat-value text-success">99.9%</div>
          </div>
        </div>
      </div>
    </div>
  )
}
