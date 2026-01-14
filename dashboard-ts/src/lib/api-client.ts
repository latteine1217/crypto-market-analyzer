import axios from 'axios';
import type { 
  Market, 
  MarketPrice, 
  MarketSummary, 
  OHLCVData, 
  OrderBookSnapshot,
  FundingRate,
  OpenInterest,
  RichListStat,
  Alert,
  DataQualityMetrics,
  NewsItem
} from '@/types/market';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add interceptors for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.error || error.message || 'An unexpected error occurred';
    const status = error.response?.status;

    console.error(`[API Error] ${status || 'Network'}: ${message}`, {
      url: error.config?.url,
      method: error.config?.method,
    });

    // We can wrap the error or add more context here
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

// Markets API
export const fetchMarkets = async (): Promise<Market[]> => {
  const response = await apiClient.get('/api/markets');
  return response.data.data;
};

export const fetchMarketPrices = async (): Promise<MarketPrice[]> => {
  const response = await apiClient.get('/api/markets/prices');
  return response.data.data;
};

export const fetchMarketQuality = async (): Promise<DataQualityMetrics[]> => {
  const response = await apiClient.get('/api/markets/quality');
  return response.data.data;
};

// News API
export const fetchNews = async (currency?: string): Promise<NewsItem[]> => {
  const response = await apiClient.get<{ data: NewsItem[] }>('/news', {
    params: { currency }
  });
  return response.data.data;
};

export interface OrderSizeData {
  time: string;
  price: number;
  avg_order_size: number;
  category: 'Big Whale' | 'Small Whale' | 'Normal' | 'Retail';
}

export const fetchOrderSizeAnalytics = async (exchange: string, symbol: string): Promise<OrderSizeData[]> => {
  const response = await apiClient.get<{ data: OrderSizeData[] }>('/analytics/order-size', {
    params: { exchange, symbol }
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
  
  const response = await apiClient.get(
    `/api/ohlcv/${exchange}/${symbol}?${params.toString()}`
  );
  return response.data.data;
};

export const fetchMarketSummary = async (
  exchange: string,
  symbol: string
): Promise<MarketSummary> => {
  const response = await apiClient.get(`/api/ohlcv/${exchange}/${symbol}/summary`);
  return response.data.data;
};

// Orderbook API
export const fetchOrderbook = async (
  exchange: string,
  symbol: string,
  limit: number = 100
): Promise<OrderBookSnapshot[]> => {
  const response = await apiClient.get(
    `/api/orderbook/${exchange}/${symbol}?limit=${limit}`
  );
  return response.data.data;
};

export const fetchLatestOrderbook = async (
  exchange: string,
  symbol: string
): Promise<OrderBookSnapshot | null> => {
  const response = await apiClient.get(`/api/orderbook/${exchange}/${symbol}/latest`);
  return response.data.data;
};

// Derivatives API
export const fetchFundingRate = async (
  exchange: string,
  symbol: string,
  limit: number = 100
): Promise<FundingRate[]> => {
  const response = await apiClient.get(
    `/api/derivatives/${exchange}/${symbol}/funding-rate?limit=${limit}`
  );
  return response.data.data;
};

export const fetchLatestFundingRate = async (
  exchange: string,
  symbol: string
): Promise<FundingRate | null> => {
  const response = await apiClient.get(
    `/api/derivatives/${exchange}/${symbol}/funding-rate/latest`
  );
  return response.data.data;
};

export const fetchOpenInterest = async (
  exchange: string,
  symbol: string,
  limit: number = 100
): Promise<OpenInterest[]> => {
  const response = await apiClient.get(
    `/api/derivatives/${exchange}/${symbol}/open-interest?limit=${limit}`
  );
  return response.data.data;
};

export const fetchLatestOpenInterest = async (
  exchange: string,
  symbol: string
): Promise<OpenInterest | null> => {
  try {
    const data = await fetchOpenInterest(exchange, symbol, 1);
    return data.length > 0 ? data[data.length - 1] : null;
  } catch (error) {
    console.error('Error fetching latest open interest:', error);
    return null;
  }
};

export const fetchRichList = async (
  symbol: string,
  days: number = 30
): Promise<RichListStat[]> => {
  const response = await apiClient.get(`/api/blockchain/${symbol}/rich-list`, { params: { days } });
  return response.data;
};

// Alerts API
export const fetchAlerts = async (): Promise<Alert[]> => {
  const response = await apiClient.get('/api/alerts');
  return response.data.data;
};

export const createAlert = async (
  symbol: string, 
  condition: 'above' | 'below', 
  target_price: number
): Promise<Alert> => {
  const response = await apiClient.post('/api/alerts', { symbol, condition, target_price });
  return response.data.data;
};

export const deleteAlert = async (id: number): Promise<void> => {
  await apiClient.delete(`/api/alerts/${id}`);
};
