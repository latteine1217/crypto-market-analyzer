/**
 * Symbol 格式統一工具
 * 處理不同交易所的 symbol 格式轉換
 */

/**
 * 解析 symbol 成 base 和 quote asset
 * 支援格式:
 * - BTC/USDT  (CCXT 標準格式)
 * - BTCUSDT   (交易所原生格式)
 * 
 * @param symbol - 交易對符號
 * @returns [baseAsset, quoteAsset]
 */
export function parseSymbol(symbol: string): [string, string] {
  // 移除可能的空白
  symbol = symbol.trim();

  // 格式 1: BTC/USDT (CCXT 標準)
  if (symbol.includes('/')) {
    const parts = symbol.split('/');
    return [parts[0], parts[1]];
  }

  // 格式 2: BTCUSDT (交易所原生)
  // 嘗試常見的 quote assets: USDT, USDC, USD, BUSD, BTC, ETH, BNB
  const quoteAssets = ['USDT', 'USDC', 'BUSD', 'USD', 'BTC', 'ETH', 'BNB', 'DAI', 'TUSD'];
  
  for (const quote of quoteAssets) {
    if (symbol.endsWith(quote)) {
      const base = symbol.slice(0, -quote.length);
      if (base.length > 0) {
        return [base, quote];
      }
    }
  }

  // 無法解析，返回錯誤標記
  throw new Error(`Unable to parse symbol: ${symbol}. Supported formats: BTC/USDT or BTCUSDT`);
}

/**
 * 標準化 symbol 為交易所原生格式 (無斜線)
 * BTC/USDT → BTCUSDT
 * BTCUSDT → BTCUSDT
 * 
 * @param symbol - 交易對符號
 * @returns 標準化後的 symbol (無斜線)
 */
export function normalizeSymbol(symbol: string): string {
  return symbol.replace('/', '');
}

/**
 * 標準化 symbol 為 CCXT 格式 (有斜線)
 * BTCUSDT → BTC/USDT
 * BTC/USDT → BTC/USDT
 * 
 * @param symbol - 交易對符號
 * @returns 標準化後的 symbol (CCXT 格式)
 */
export function toCcxtFormat(symbol: string): string {
  if (symbol.includes('/')) {
    return symbol;
  }

  const [base, quote] = parseSymbol(symbol);
  return `${base}/${quote}`;
}

/**
 * 驗證 symbol 格式是否正確
 * 
 * @param symbol - 交易對符號
 * @returns 是否為有效的 symbol
 */
export function isValidSymbol(symbol: string): boolean {
  try {
    parseSymbol(symbol);
    return true;
  } catch {
    return false;
  }
}
