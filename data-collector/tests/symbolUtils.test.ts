/**
 * Unit tests for symbol utility functions
 */
import {
  parseSymbol,
  normalizeSymbol,
  toCcxtFormat,
  isValidSymbol
} from '../utils/symbolUtils';

describe('parseSymbol', () => {
  describe('CCXT format (BTC/USDT)', () => {
    it('should parse BTC/USDT correctly', () => {
      const [base, quote] = parseSymbol('BTC/USDT');
      expect(base).toBe('BTC');
      expect(quote).toBe('USDT');
    });

    it('should parse ETH/BTC correctly', () => {
      const [base, quote] = parseSymbol('ETH/BTC');
      expect(base).toBe('ETH');
      expect(quote).toBe('BTC');
    });
  });

  describe('Native format (BTCUSDT)', () => {
    it('should parse BTCUSDT correctly', () => {
      const [base, quote] = parseSymbol('BTCUSDT');
      expect(base).toBe('BTC');
      expect(quote).toBe('USDT');
    });

    it('should parse ETHUSDC correctly', () => {
      const [base, quote] = parseSymbol('ETHUSDC');
      expect(base).toBe('ETH');
      expect(quote).toBe('USDC');
    });

    it('should parse ETHBTC correctly', () => {
      const [base, quote] = parseSymbol('ETHBTC');
      expect(base).toBe('ETH');
      expect(quote).toBe('BTC');
    });
  });

  describe('Whitespace handling', () => {
    it('should handle leading/trailing whitespace', () => {
      const [base, quote] = parseSymbol('  BTC/USDT  ');
      expect(base).toBe('BTC');
      expect(quote).toBe('USDT');
    });
  });

  describe('Invalid formats', () => {
    it('should throw error for unparseable symbol', () => {
      expect(() => parseSymbol('INVALID')).toThrow('Unable to parse symbol');
    });

    it('should throw error for empty string', () => {
      expect(() => parseSymbol('')).toThrow('Unable to parse symbol');
    });
  });

  describe('Multiple trading pairs', () => {
    const testCases: Array<[string, string, string]> = [
      ['SOL/USDT', 'SOL', 'USDT'],
      ['SOLUSDT', 'SOL', 'USDT'],
      ['BNB/BUSD', 'BNB', 'BUSD'],
      ['BNBBUSD', 'BNB', 'BUSD'],
      ['LINK/ETH', 'LINK', 'ETH'],
      ['LINKETH', 'LINK', 'ETH'],
    ];

    testCases.forEach(([symbol, expectedBase, expectedQuote]) => {
      it(`should parse ${symbol} as ${expectedBase}/${expectedQuote}`, () => {
        const [base, quote] = parseSymbol(symbol);
        expect(base).toBe(expectedBase);
        expect(quote).toBe(expectedQuote);
      });
    });
  });
});

describe('normalizeSymbol', () => {
  it('should convert CCXT format to native format', () => {
    expect(normalizeSymbol('BTC/USDT')).toBe('BTCUSDT');
    expect(normalizeSymbol('ETH/BTC')).toBe('ETHBTC');
  });

  it('should keep native format unchanged', () => {
    expect(normalizeSymbol('BTCUSDT')).toBe('BTCUSDT');
    expect(normalizeSymbol('ETHBTC')).toBe('ETHBTC');
  });

  it('should handle multiple slashes (edge case)', () => {
    expect(normalizeSymbol('A/B/C')).toBe('ABC');
  });
});

describe('toCcxtFormat', () => {
  it('should convert native format to CCXT format', () => {
    expect(toCcxtFormat('BTCUSDT')).toBe('BTC/USDT');
    expect(toCcxtFormat('ETHBTC')).toBe('ETH/BTC');
  });

  it('should keep CCXT format unchanged', () => {
    expect(toCcxtFormat('BTC/USDT')).toBe('BTC/USDT');
    expect(toCcxtFormat('ETH/BTC')).toBe('ETH/BTC');
  });

  it('should handle various quote assets', () => {
    expect(toCcxtFormat('ETHUSDC')).toBe('ETH/USDC');
    expect(toCcxtFormat('BNBBUSD')).toBe('BNB/BUSD');
    expect(toCcxtFormat('LINKETH')).toBe('LINK/ETH');
  });
});

describe('isValidSymbol', () => {
  describe('Valid symbols', () => {
    const validSymbols = [
      'BTC/USDT',
      'BTCUSDT',
      'ETH/BTC',
      'ETHBTC',
      'SOL/USDC',
      'SOLUSDC',
    ];

    validSymbols.forEach((symbol) => {
      it(`should validate ${symbol} as true`, () => {
        expect(isValidSymbol(symbol)).toBe(true);
      });
    });
  });

  describe('Invalid symbols', () => {
    const invalidSymbols = [
      'INVALID',
      'ABC',
      'XYZ123',
      '',
      '   ',
      '123/456',
    ];

    invalidSymbols.forEach((symbol) => {
      it(`should validate "${symbol}" as false`, () => {
        expect(isValidSymbol(symbol)).toBe(false);
      });
    });
  });
});

describe('Edge cases', () => {
  it('should handle short base asset (DOT)', () => {
    const [base, quote] = parseSymbol('DOTUSDT');
    expect(base).toBe('DOT');
    expect(quote).toBe('USDT');
  });

  it('should handle long base asset (SHIB)', () => {
    const [base, quote] = parseSymbol('SHIBUSDT');
    expect(base).toBe('SHIB');
    expect(quote).toBe('USDT');
  });

  it('should be case-sensitive', () => {
    const [base, quote] = parseSymbol('BTC/USDT');
    expect(base).toBe('BTC'); // uppercase
    expect(quote).toBe('USDT'); // uppercase
  });
});

describe('Round-trip conversions', () => {
  it('CCXT → Native → CCXT should be consistent', () => {
    const original = 'BTC/USDT';
    const native = normalizeSymbol(original);
    const back = toCcxtFormat(native);
    expect(back).toBe(original);
  });

  it('Native → CCXT → Native should be consistent', () => {
    const original = 'BTCUSDT';
    const ccxt = toCcxtFormat(original);
    const back = normalizeSymbol(ccxt);
    expect(back).toBe(original);
  });
});
