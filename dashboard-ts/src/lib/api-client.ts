import axios from 'axios';
import type { 
  Market, 
  OHLCVData, 
  OrderBookSnapshot,
  FundingRate,
  OpenInterest,
  RichListStat,
  Alert,
  DataQualityMetrics,
  FearGreedData,
  ETFProduct,
  ETFIssuer,
  ETFFlowAnalyticsResponse
} from '@/types/market';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '/api';

const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 攔截器：處理錯誤
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.error || error.message || 'An unexpected error occurred';
    const status = error.response?.status;

    console.error(`[API Error] ${status || 'Network'}: ${message}`, {
      url: error.config?.url,
      method: error.config?.method,
    });

    if (status === 404) {
      console.warn('Resource not found');
    } else if (status === 429) {
      console.error('Rate limit exceeded');
    } else if (status >= 500) {
      console.error('Server error');
    }

    return Promise.reject(error);
  }
);

// System Status API
export interface SystemStatus {
  services: {
    database: { status: string; total_records: number; db_size: string };
    redis: { status: string; uptime: number; memory_used: string };
    api_server: { 
      status: string; 
      uptime: number; 
      api_latency_ms: number;
      env: string;
      node_version: string;
    };
  };
  collectors: {
    exchange: string;
    symbol: string;
    last_data_time: string;
    is_active: boolean;
  }[];
  timestamp: string;
}

export const fetchSystemStatus = async (): Promise<SystemStatus> => {
  const response = await apiClient.get<{ data: SystemStatus }>('/status');
  return response.data.data;
};

// Markets API
export const fetchMarkets = async (): Promise<Market[]> => {
  const response = await apiClient.get<{ data: Market[] }>('/markets');
  return response.data.data;
};

export const fetchMarketQuality = async (): Promise<DataQualityMetrics[]> => {
  const response = await apiClient.get<{ data: DataQualityMetrics[] }>('/markets/quality');
  return response.data.data;
};

// Analytics API
export interface OrderSizeData {
  time: string;
  price: number;
  avg_buy_size: number;
  avg_sell_size: number;
  category: 'Big Whale' | 'Small Whale' | 'Retail';
}

export const fetchOrderSizeAnalytics = async (exchange: string, symbol: string): Promise<OrderSizeData[]> => {
  const response = await apiClient.get<{ data: OrderSizeData[] }>('/analytics/order-size', {
    params: { exchange, symbol }
  });
  return response.data.data;
};

export interface CVDData {
  time: string;
  delta: number;
  cvd: number;
  buy_volume: number;
  sell_volume: number;
}

export const fetchCVD = async (
  exchange: string,
  symbol: string,
  interval: string = '1m',
  limit: number = 1000
): Promise<CVDData[]> => {
  const response = await apiClient.get<{ data: CVDData[] }>('/analytics/cvd', {
    params: { exchange, symbol, interval, limit }
  });
  return response.data.data;
};

// OHLCV API
export const fetchOHLCV = async (
  exchange: string,
  symbol: string,
  options?: { timeframe?: string; limit?: number }
): Promise<OHLCVData[]> => {
  const params = new URLSearchParams({
    timeframe: options?.timeframe || '1m',
    limit: String(options?.limit || 500),
  });
  
  const response = await apiClient.get<{ data: OHLCVData[] }>(
    `/ohlcv/${exchange}/${symbol}?${params.toString()}`
  );
  return response.data.data;
};

// Orderbook API
export const fetchLatestOrderbook = async (
  exchange: string,
  symbol: string
): Promise<OrderBookSnapshot | null> => {
  const response = await apiClient.get<{ data: OrderBookSnapshot | null }>(`/orderbook/${exchange}/${symbol}/latest`);
  return response.data.data;
};

export interface OBIData {
  time: string;
  obi: number;
  spread: number;
  mid_price: number;
}

export const fetchOBI = async (
  exchange: string,
  symbol: string,
  limit: number = 100
): Promise<OBIData[]> => {
  const response = await apiClient.get<{ data: OBIData[] }>(
    `/orderbook/${exchange}/${symbol}`,
    { params: { limit } }
  );
  return response.data.data;
};

// Derivatives API
export const fetchFundingRate = async (
  exchange: string,
  symbol: string,
  limit: number = 100
): Promise<FundingRate[]> => {
  const response = await apiClient.get<{ data: FundingRate[] }>(
    `/derivatives/${exchange}/${symbol}/funding-rate?limit=${limit}`
  );
  return response.data.data;
};

export const fetchOpenInterest = async (
  exchange: string,
  symbol: string,
  limit: number = 100
): Promise<OpenInterest[]> => {
  const response = await apiClient.get<{ data: OpenInterest[] }>(
    `/derivatives/${exchange}/${symbol}/open-interest?limit=${limit}`
  );
  return response.data.data;
};

export const fetchLiquidations = async (
  exchange: string,
  symbol: string,
  limit: number = 200
): Promise<any[]> => {
  const response = await apiClient.get<{ data: any[] }>(
    `/derivatives/${exchange}/${symbol}/liquidations?limit=${limit}`
  );
  return response.data.data;
};

// Blockchain API
export const fetchRichList = async (
  symbol: string,
  days: number = 30
): Promise<RichListStat[]> => {
  const response = await apiClient.get<{ data: RichListStat[] }>(`/blockchain/${symbol}/rich-list`, { params: { days } });
  return response.data.data;
};

export interface WhaleTransaction {
  timestamp: string;
  tx_hash: string;
  from_addr: string;
  to_addr: string;
  amount_usd: number;
  asset: string;
  blockchain: string;
}

export const fetchWhaleTransactions = async (limit: number = 50): Promise<WhaleTransaction[]> => {
  const response = await apiClient.get<{ data: WhaleTransaction[] }>('/blockchain/whales/recent', {
    params: { limit }
  });
  return response.data.data;
};

// Fear & Greed API
export const fetchFearGreed = async (): Promise<FearGreedData | null> => {
  const response = await apiClient.get<{ data: FearGreedData | null }>('/fear-greed/latest');
  return response.data.data;
};

// ETF API
export const fetchETFProducts = async (asset: string, days: number): Promise<ETFProduct[]> => {
  const response = await apiClient.get<{ data: ETFProduct[] }>('/etf-flows/products', {
    params: { asset, days }
  });
  return response.data.data;
};

export const fetchTopIssuers = async (asset: string, days: number): Promise<ETFIssuer[]> => {
  const response = await apiClient.get<{ data: ETFIssuer[] }>('/etf-flows/top-issuers', {
    params: { asset, days }
  });
  return response.data.data;
};

export const fetchETFAnalytics = async (asset: string, days: number): Promise<ETFFlowAnalyticsResponse> => {
  const response = await apiClient.get<ETFFlowAnalyticsResponse>('/etf-flows/analytics', {
    params: { asset, days }
  });
  return response.data;
};

// Alerts API
export const fetchAlerts = async (): Promise<Alert[]> => {
  const response = await apiClient.get<{ data: Alert[] }>('/alerts');
  return response.data.data;
};

export const createAlert = async (
  symbol: string, 
  condition: 'above' | 'below', 
  target_price: number
): Promise<Alert> => {
  const response = await apiClient.post<{ data: Alert }>('/alerts', { symbol, condition, target_price });
  return response.data.data;
};

export const deleteAlert = async (id: number): Promise<void> => {
  await apiClient.delete(`/alerts/${id}`);
};

export interface MarketSignal {
  time: string;
  symbol: string;
  signal_type: string;
  side: string;
  severity: string;
  price_at_signal: number;
  message: string;
  metadata: any;
}

export const fetchSignals = async (
  symbol?: string,
  limit: number = 50
): Promise<MarketSignal[]> => {
  const response = await apiClient.get<{ data: MarketSignal[] }>('/alerts/signals', {
    params: { symbol, limit }
  });
  return response.data.data;
};
