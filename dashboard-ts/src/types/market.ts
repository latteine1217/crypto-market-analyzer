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
  open_interest?: number
  open_interest_usd?: number
  funding_rate?: number
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
  data: WSTradeData | WSOrderBookData | WSPriceData
  timestamp: string
}

// WebSocket Data Types
export interface WSTradeData {
  price: number
  quantity: number
  side: 'buy' | 'sell'
  tradeId?: string
}

export interface WSOrderBookData {
  bids: OrderBookLevel[]
  asks: OrderBookLevel[]
  updateId?: number
}

export interface WSPriceData {
  price: number
  volume?: number
}

export interface RichListStat {
  snapshot_date: string
  timestamp?: string
  rank_group: string
  tier_name?: string
  address_count: number
  total_balance: number
  total_balance_usd?: number | null
  percentage_of_supply?: number | null
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

export interface DataQualityMetrics {
  exchange: string
  symbol: string
  timeframe: string
  check_time: string
  missing_rate: number
  quality_score: number
  status: 'excellent' | 'good' | 'acceptable' | 'poor' | 'critical'
  missing_count: number
  expected_count: number
  actual_count: number
  backfill_task_created: boolean
}

// Macro & Sentiment Types
export interface FearGreedData {
  timestamp: string
  value: number
  classification: string
  description: string
}

export interface ETFProduct {
  date: string
  product_code: string;
  product_name: string;
  issuer: string;
  net_flow_usd: number;
  total_aum_usd: number | null;
}

export interface ETFIssuer {
  issuer: string;
  product_count: number;
  total_net_flow_usd: number;
  avg_daily_flow_usd: number;
}

export interface ETFFlowAnalyticsRow {
  date: string;
  total_net_flow_usd: number;
  cumulative_flow_usd: number;
  product_count: number;
  btc_close: number | null;
  net_flow_btc: number | null;
  flow_pct_aum: number | null;
  flow_pct_20d_avg: number | null;
  flow_zscore: number | null;
  flow_shock: boolean;
  issuer_concentration_top1: number | null;
  issuer_concentration_top2: number | null;
  issuer_concentration_top3: number | null;
  gbtc_vs_ibit_divergence: number | null;
  price_change: number | null;
  price_divergence: 'price_up_outflow' | 'price_down_inflow' | null;
}

export interface ETFWeeklyDivergence {
  week_start: string;
  divergence_usd: number;
}

export interface ETFFlowAnalyticsMeta {
  inflow_streak: number;
  outflow_streak: number;
  latest_flow: number;
  last_update_time: string | null;
  staleness_hours: number | null;
  quality_status: 'fresh' | 'stale';
  weekly_divergence: ETFWeeklyDivergence[];
}

export interface ETFFlowAnalyticsResponse {
  data: ETFFlowAnalyticsRow[];
  meta: ETFFlowAnalyticsMeta;
}
