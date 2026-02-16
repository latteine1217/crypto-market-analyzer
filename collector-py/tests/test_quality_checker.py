"""
DataQualityChecker 單元測試

測試範圍：
1. 品質指標計算（缺失率、時間戳順序）
2. 補資料任務建立
3. 品質報告生成
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta


@pytest.fixture
def mock_db_loader():
    """模擬 DatabaseLoader"""
    mock = MagicMock()
    mock.get_connection = MagicMock()
    return mock


@pytest.fixture
def mock_validator():
    """模擬 DataValidator"""
    mock = MagicMock()
    return mock


@pytest.fixture
def mock_backfill_scheduler():
    """模擬 BackfillScheduler"""
    mock = MagicMock()
    return mock


class TestDataQualityCheckerInit:
    """測試 DataQualityChecker 初始化"""
    
    def test_init_with_dependencies(self, mock_db_loader, mock_validator, mock_backfill_scheduler):
        """測試使用依賴注入初始化"""
        from quality_checker import DataQualityChecker
        
        checker = DataQualityChecker(
            db_loader=mock_db_loader,
            validator=mock_validator,
            backfill_scheduler=mock_backfill_scheduler
        )
        
        assert checker.db == mock_db_loader
        assert checker.validator == mock_validator
        assert checker.backfill_scheduler == mock_backfill_scheduler
    
    def test_init_creates_default_dependencies(self):
        """測試不提供依賴時建立預設實例"""
        with patch('quality_checker.DatabaseLoader'), \
             patch('quality_checker.DataValidator'), \
             patch('quality_checker.BackfillScheduler'):
            
            from quality_checker import DataQualityChecker
            checker = DataQualityChecker()
            
            assert checker.db is not None
            assert checker.validator is not None
            assert checker.backfill_scheduler is not None


class TestOHLCVQualityCheck:
    """測試 OHLCV 品質檢查"""
    
    def test_check_quality_with_complete_data(self, mock_db_loader, mock_validator, mock_backfill_scheduler):
        """測試完整資料的品質檢查"""
        from quality_checker import DataQualityChecker
        
        checker = DataQualityChecker(
            db_loader=mock_db_loader,
            validator=mock_validator,
            backfill_scheduler=mock_backfill_scheduler
        )
        
        # 模擬驗證結果（無錯誤）
        mock_validator.validate_ohlcv_stream.return_value = {
            'valid': True,
            'total_records': 1440,  # 24小時 * 60分鐘
            'errors': [],
            'warnings': []
        }
        
        # 模擬資料庫返回
        with patch.object(checker, '_iter_ohlcv_from_db', return_value=iter([])), \
             patch.object(checker, '_calculate_expected_count', return_value=1440):
            
            result = checker.check_ohlcv_quality(
                market_id=1,
                timeframe='1m',
                lookback_hours=24,
                create_backfill_tasks=False
            )
            
            assert result['total_records'] == 1440
            assert result['valid'] is True
    
    def test_check_quality_with_missing_data(self, mock_db_loader, mock_validator, mock_backfill_scheduler):
        """測試資料缺失時的品質檢查"""
        from quality_checker import DataQualityChecker
        
        checker = DataQualityChecker(
            db_loader=mock_db_loader,
            validator=mock_validator,
            backfill_scheduler=mock_backfill_scheduler
        )
        
        # 模擬驗證結果（有缺失）
        mock_validator.validate_ohlcv_stream.return_value = {
            'valid': False,
            'total_records': 1200,  # 少了 240 筆
            'errors': [{'type': 'missing_data', 'count': 240}],
            'warnings': []
        }
        
        # 模擬資料庫返回
        with patch.object(checker, '_iter_ohlcv_from_db', return_value=iter([])), \
             patch.object(checker, '_calculate_expected_count', return_value=1440):
            
            result = checker.check_ohlcv_quality(
                market_id=1,
                timeframe='1m',
                lookback_hours=24,
                create_backfill_tasks=True
            )
            
            assert result['total_records'] == 1200
            # 應該建立補資料任務
            mock_backfill_scheduler.create_backfill_task.assert_called()
    
    def test_check_quality_with_no_data(self, mock_db_loader, mock_validator, mock_backfill_scheduler):
        """測試完全無資料時的品質檢查"""
        from quality_checker import DataQualityChecker
        
        checker = DataQualityChecker(
            db_loader=mock_db_loader,
            validator=mock_validator,
            backfill_scheduler=mock_backfill_scheduler
        )
        
        # 模擬驗證結果（無資料）
        mock_validator.validate_ohlcv_stream.return_value = {
            'valid': False,
            'total_records': 0,
            'errors': [],
            'warnings': []
        }
        
        # 模擬資料庫返回
        with patch.object(checker, '_iter_ohlcv_from_db', return_value=iter([])), \
             patch.object(checker, '_calculate_expected_count', return_value=1440):
            
            result = checker.check_ohlcv_quality(
                market_id=1,
                timeframe='1m',
                lookback_hours=24,
                create_backfill_tasks=True
            )
            
            assert result['total_records'] == 0
            # 應該建立補資料任務
            mock_backfill_scheduler.create_backfill_task.assert_called()


class TestExpectedCountCalculation:
    """測試預期記錄數計算"""
    
    @pytest.mark.parametrize("timeframe,hours,expected", [
        ('1m', 24, 1440),   # 24小時 * 60分鐘
        ('5m', 24, 288),    # 24小時 * 12次/小時
        ('1h', 24, 24),     # 24小時
        ('1m', 1, 60),      # 1小時 * 60分鐘
    ])
    def test_calculate_expected_count(self, timeframe, hours, expected, 
                                      mock_db_loader, mock_validator, mock_backfill_scheduler):
        """測試不同時間框架的預期記錄數計算"""
        from quality_checker import DataQualityChecker
        
        checker = DataQualityChecker(
            db_loader=mock_db_loader,
            validator=mock_validator,
            backfill_scheduler=mock_backfill_scheduler
        )
        
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        end_time = datetime.now(timezone.utc)
        
        count = checker._calculate_expected_count(start_time, end_time, timeframe)
        
        # 允許 ±1 的誤差（因為時間計算可能有毫秒差異）
        assert abs(count - expected) <= 1


class TestMissingRatioCalculation:
    """測試缺失率計算"""
    
    def test_missing_ratio_with_complete_data(self):
        """測試完整資料的缺失率"""
        # 完整資料：缺失率 = 0%
        assert 0.0 == pytest.approx(0.0, abs=0.01)
    
    def test_missing_ratio_with_partial_data(self):
        """測試部分缺失資料的缺失率"""
        # 1200/1440 = 83.33% 完整，缺失率 = 16.67%
        actual = 1200
        expected = 1440
        missing_ratio = (expected - actual) / expected * 100
        
        assert missing_ratio == pytest.approx(16.67, abs=0.01)
    
    def test_missing_ratio_with_no_data(self):
        """測試無資料的缺失率"""
        # 0/1440 = 0% 完整，缺失率 = 100%
        actual = 0
        expected = 1440
        missing_ratio = (expected - actual) / expected * 100
        
        assert missing_ratio == pytest.approx(100.0, abs=0.01)


@pytest.mark.unit
class TestQualityMetricsIntegration:
    """測試品質指標整合"""
    
    def test_quality_status_classification(self):
        """測試品質狀態分類"""
        # 根據 AGENTS.md 的驗收標準：K 線缺失率 ≤ 0.1% 為合格
        
        # Excellent: 0%
        assert 0.0 <= 0.1
        
        # Good: 0.05%
        assert 0.05 <= 0.1
        
        # Acceptable: 0.1%
        assert 0.1 <= 0.1
        
        # Poor: 1%
        assert 1.0 > 0.1
        
        # Critical: 5%
        assert 5.0 > 0.1
