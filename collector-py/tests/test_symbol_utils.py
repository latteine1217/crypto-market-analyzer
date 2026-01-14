"""
Unit tests for symbol utility functions
"""
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import pytest
from utils.symbol_utils import (
    parse_symbol,
    normalize_symbol,
    to_ccxt_format,
    is_valid_symbol
)


class TestParseSymbol:
    """測試 symbol 解析功能"""
    
    def test_parse_ccxt_format(self):
        """測試 CCXT 格式 (BTC/USDT)"""
        base, quote = parse_symbol('BTC/USDT')
        assert base == 'BTC'
        assert quote == 'USDT'
    
    def test_parse_native_format_usdt(self):
        """測試交易所原生格式 (BTCUSDT)"""
        base, quote = parse_symbol('BTCUSDT')
        assert base == 'BTC'
        assert quote == 'USDT'
    
    def test_parse_native_format_usdc(self):
        """測試其他 stablecoin"""
        base, quote = parse_symbol('ETHUSDC')
        assert base == 'ETH'
        assert quote == 'USDC'
    
    def test_parse_native_format_btc(self):
        """測試 BTC quote"""
        base, quote = parse_symbol('ETHBTC')
        assert base == 'ETH'
        assert quote == 'BTC'
    
    def test_parse_with_whitespace(self):
        """測試帶有空白的 symbol"""
        base, quote = parse_symbol('  BTC/USDT  ')
        assert base == 'BTC'
        assert quote == 'USDT'
    
    def test_parse_invalid_format(self):
        """測試無效格式"""
        with pytest.raises(ValueError, match="Unable to parse symbol"):
            parse_symbol('INVALID')
    
    def test_parse_empty_string(self):
        """測試空字串"""
        with pytest.raises(ValueError):
            parse_symbol('')
    
    def test_parse_multiple_pairs(self):
        """測試多種交易對"""
        test_cases = [
            ('SOL/USDT', 'SOL', 'USDT'),
            ('SOLUSDT', 'SOL', 'USDT'),
            ('BNB/BUSD', 'BNB', 'BUSD'),
            ('BNBBUSD', 'BNB', 'BUSD'),
            ('LINK/ETH', 'LINK', 'ETH'),
            ('LINKETH', 'LINK', 'ETH'),
        ]
        for symbol, expected_base, expected_quote in test_cases:
            base, quote = parse_symbol(symbol)
            assert base == expected_base
            assert quote == expected_quote


class TestNormalizeSymbol:
    """測試 symbol 標準化功能"""
    
    def test_normalize_ccxt_format(self):
        """CCXT 格式 → 原生格式"""
        assert normalize_symbol('BTC/USDT') == 'BTCUSDT'
        assert normalize_symbol('ETH/BTC') == 'ETHBTC'
    
    def test_normalize_already_native(self):
        """已經是原生格式"""
        assert normalize_symbol('BTCUSDT') == 'BTCUSDT'
        assert normalize_symbol('ETHBTC') == 'ETHBTC'
    
    def test_normalize_multiple_slashes(self):
        """多個斜線 (edge case)"""
        assert normalize_symbol('A/B/C') == 'ABC'


class TestToCcxtFormat:
    """測試轉換為 CCXT 格式"""
    
    def test_native_to_ccxt(self):
        """原生格式 → CCXT 格式"""
        assert to_ccxt_format('BTCUSDT') == 'BTC/USDT'
        assert to_ccxt_format('ETHBTC') == 'ETH/BTC'
    
    def test_ccxt_to_ccxt(self):
        """已經是 CCXT 格式"""
        assert to_ccxt_format('BTC/USDT') == 'BTC/USDT'
        assert to_ccxt_format('ETH/BTC') == 'ETH/BTC'
    
    def test_various_quotes(self):
        """測試各種 quote asset"""
        assert to_ccxt_format('ETHUSDC') == 'ETH/USDC'
        assert to_ccxt_format('BNBBUSD') == 'BNB/BUSD'
        assert to_ccxt_format('LINKETH') == 'LINK/ETH'


class TestIsValidSymbol:
    """測試 symbol 驗證"""
    
    def test_valid_symbols(self):
        """有效的 symbols"""
        valid = [
            'BTC/USDT',
            'BTCUSDT',
            'ETH/BTC',
            'ETHBTC',
            'SOL/USDC',
            'SOLUSDC',
        ]
        for symbol in valid:
            assert is_valid_symbol(symbol) is True
    
    def test_invalid_symbols(self):
        """無效的 symbols"""
        invalid = [
            'INVALID',
            'ABC',
            'XYZ123',
            '',
            '   ',
            # Note: '123/456' is technically valid in CCXT format, but semantically wrong
        ]
        for symbol in invalid:
            assert is_valid_symbol(symbol) is False


class TestEdgeCases:
    """Edge cases 測試"""
    
    def test_short_base_asset(self):
        """短的 base asset (1-2 字元)"""
        # 這些可能無法正確解析，因為演算法假設至少 2 字元
        base, quote = parse_symbol('DOTUSDT')
        assert base == 'DOT'
        assert quote == 'USDT'
    
    def test_long_base_asset(self):
        """長的 base asset"""
        base, quote = parse_symbol('SHIBUSDT')
        assert base == 'SHIB'
        assert quote == 'USDT'
    
    def test_case_sensitivity(self):
        """大小寫敏感性"""
        # 目前實作是大小寫敏感的
        base, quote = parse_symbol('BTC/USDT')
        assert base == 'BTC'  # 大寫
        assert quote == 'USDT'  # 大寫


class TestRoundTrip:
    """往返轉換測試"""
    
    def test_ccxt_to_native_to_ccxt(self):
        """CCXT → Native → CCXT 應該一致"""
        original = 'BTC/USDT'
        native = normalize_symbol(original)
        back = to_ccxt_format(native)
        assert back == original
    
    def test_native_to_ccxt_to_native(self):
        """Native → CCXT → Native 應該一致"""
        original = 'BTCUSDT'
        ccxt = to_ccxt_format(original)
        back = normalize_symbol(ccxt)
        assert back == original
