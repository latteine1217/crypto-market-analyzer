// OHLCV Data Types
export interface OHLCVData {
  timestamp: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface OHLCVWithIndicators extends OHLCVData {
  sma_20?: number
  sma_50?: number
  sma_60?: number
  sma_200?: number
  ema_12?: number
  ema_26?: number
  rsi_14?: number
  macd?: number
  macd_signal?: number
  macd_hist?: number
  bollinger_upper?: number
  bollinger_middle?: number
  bollinger_lower?: number
  fractal_up?: boolean
  fractal_down?: boolean
}

// Market Data Types
export interface Market {
  id: number
  exchange_id: number
  exchange: string
  symbol: string
  base_asset: string
  quote_asset: string
  is_active: boolean
  created_at: string
}

export interface MarketPrice {
  exchange: string
  symbol: string
  price: number
  change_24h: number
  volume_24h: number
  high_24h?: number
  low_24h?: number
}

export interface MarketSummary {
  latest_price: number
  change_24h: number
  volume_24h: number
  high_24h: number
  low_24h: number
  macd: number | null
  macd_signal: number | null
  ma_20: number | null
  ma_60: number | null
  rsi_14: number | null
}

// Derivatives Data Types
export interface FundingRate {
  timestamp: string
  funding_rate: number
  funding_rate_daily: number
  mark_price: number
  index_price: number
  next_funding_time: string
}

export interface OpenInterest {
  timestamp: string
  open_interest: number
  open_interest_usd: number | null
  open_interest_change_24h: number | null
  open_interest_change_pct: number | null
  price: number | null
  volume_24h: number | null
}

// Order Book Types
export interface OrderBookLevel {
  price: number
  quantity: number
}

export interface OrderBookSnapshot {
  timestamp: string
  bids: OrderBookLevel[]
  asks: OrderBookLevel[]
}

// API Response Types
export interface APIResponse<T> {
  data: T
  error?: string
  timestamp: string
}

// WebSocket Message Types
export interface WSMessage {
  type: 'price' | 'trade' | 'orderbook'
  exchange: string
  symbol: string
  data: any
  timestamp: string
}

export interface RichListStat {
  snapshot_date: string
  rank_group: string
  address_count: number
  total_balance: number
  total_balance_usd: number
  percentage_of_supply: number
}

export interface Alert {
  id: number
  symbol: string
  condition: 'above' | 'below'
  target_price: number
  is_active: boolean
  is_triggered: boolean
  triggered_at: string | null
  created_at: string
}
