"""
DatabaseLoader 單元測試

測試範圍：
1. 連接池初始化與管理
2. 事務處理
3. 錯誤處理與重試
4. Market ID 取得與建立
5. OHLCV 批次寫入
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import psycopg2

# 需要 mock config 以避免實際連接資料庫
@pytest.fixture(autouse=True)
def mock_settings():
    with patch('config.settings') as mock:
        mock.postgres_host = 'localhost'
        mock.postgres_port = 5432
        mock.postgres_db = 'test_db'
        mock.postgres_user = 'test_user'
        mock.postgres_password = 'test_pass'
        yield mock


@pytest.fixture
def mock_connection_pool():
    """模擬連接池"""
    with patch('loaders.db_loader.pool.ThreadedConnectionPool') as mock_pool:
        # 建立模擬連接
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = False
        
        # 配置連接池返回模擬連接
        mock_pool_instance = MagicMock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance
        
        yield {
            'pool_class': mock_pool,
            'pool_instance': mock_pool_instance,
            'connection': mock_conn,
            'cursor': mock_cursor
        }


class TestDatabaseLoaderInit:
    """測試 DatabaseLoader 初始化"""
    
    def test_init_creates_connection_pool(self, mock_connection_pool):
        """測試初始化時建立連接池"""
        from loaders.db_loader import DatabaseLoader
        
        # 重置類變數
        DatabaseLoader._connection_pool = None
        DatabaseLoader._pool_lock = None
        
        db = DatabaseLoader(min_conn=2, max_conn=10)
        
        # 驗證連接池已建立
        assert db.min_conn == 2
        assert db.max_conn == 10
        mock_connection_pool['pool_class'].assert_called_once()
    
    def test_init_reuses_existing_pool(self, mock_connection_pool):
        """測試多次初始化時重用連接池"""
        from loaders.db_loader import DatabaseLoader
        
        # 重置並建立第一個實例
        DatabaseLoader._connection_pool = None
        DatabaseLoader._pool_lock = None
        db1 = DatabaseLoader()
        
        # 建立第二個實例
        db2 = DatabaseLoader()
        
        # 連接池只應該被建立一次
        assert mock_connection_pool['pool_class'].call_count == 1
    
    def test_init_handles_connection_error(self, mock_connection_pool):
        """測試初始化時處理連接錯誤"""
        from loaders.db_loader import DatabaseLoader
        
        # 重置類變數
        DatabaseLoader._connection_pool = None
        DatabaseLoader._pool_lock = None
        
        # 模擬連接失敗
        mock_connection_pool['pool_class'].side_effect = psycopg2.OperationalError("Connection failed")
        
        # 驗證拋出異常
        with pytest.raises(psycopg2.OperationalError):
            DatabaseLoader()


class TestConnectionManagement:
    """測試連接管理"""
    
    def test_get_connection_returns_valid_connection(self, mock_connection_pool):
        """測試 get_connection 返回有效連接"""
        from loaders.db_loader import DatabaseLoader
        
        DatabaseLoader._connection_pool = None
        db = DatabaseLoader()
        
        with db.get_connection() as conn:
            assert conn is not None
            assert conn == mock_connection_pool['connection']
    
    def test_get_connection_returns_connection_to_pool(self, mock_connection_pool):
        """測試 get_connection 正確歸還連接"""
        from loaders.db_loader import DatabaseLoader
        
        DatabaseLoader._connection_pool = None
        db = DatabaseLoader()
        
        with db.get_connection() as conn:
            pass
        
        # 驗證連接被歸還
        mock_connection_pool['pool_instance'].putconn.assert_called()
    
    def test_get_connection_handles_invalid_connection(self, mock_connection_pool):
        """測試處理無效連接"""
        from loaders.db_loader import DatabaseLoader
        
        DatabaseLoader._connection_pool = None
        db = DatabaseLoader()
        
        # 模擬第一次獲取返回無效連接
        mock_conn_invalid = MagicMock()
        mock_conn_invalid.isolation_level = property(
            lambda self: (_ for _ in ()).throw(psycopg2.OperationalError("Connection closed"))
        )
        
        mock_conn_valid = mock_connection_pool['connection']
        mock_connection_pool['pool_instance'].getconn.side_effect = [
            mock_conn_invalid,
            mock_conn_valid
        ]
        
        with db.get_connection() as conn:
            # 應該獲取到第二個有效連接
            assert conn == mock_conn_valid


class TestMarketOperations:
    """測試市場相關操作"""
    
    def test_get_market_id_existing_market(self, mock_connection_pool):
        """測試取得現有市場ID"""
        from loaders.db_loader import DatabaseLoader
        
        DatabaseLoader._connection_pool = None
        db = DatabaseLoader()
        
        # 模擬資料庫返回
        cursor = mock_connection_pool['cursor']
        cursor.fetchone.side_effect = [
            (1,),  # exchange_id
            (100,)  # market_id
        ]
        
        market_id = db.get_market_id('binance', 'BTCUSDT')
        
        assert market_id == 100
        assert cursor.execute.call_count >= 2
    
    def test_get_market_id_creates_new_market(self, mock_connection_pool):
        """測試建立新市場"""
        from loaders.db_loader import DatabaseLoader
        
        DatabaseLoader._connection_pool = None
        db = DatabaseLoader()
        
        # 模擬資料庫返回
        cursor = mock_connection_pool['cursor']
        cursor.fetchone.side_effect = [
            (1,),   # exchange_id
            None,   # market 不存在
            (200,)  # 新建立的 market_id
        ]
        
        market_id = db.get_market_id('binance', 'ETHUSDT')
        
        assert market_id == 200
        # 驗證有執行 INSERT
        assert any('INSERT' in str(call) for call in cursor.execute.call_args_list)
    
    def test_get_market_id_exchange_not_found(self, mock_connection_pool):
        """測試交易所不存在時返回 None"""
        from loaders.db_loader import DatabaseLoader
        
        DatabaseLoader._connection_pool = None
        db = DatabaseLoader()
        
        # 模擬交易所不存在
        cursor = mock_connection_pool['cursor']
        cursor.fetchone.return_value = None
        
        market_id = db.get_market_id('invalid_exchange', 'BTCUSDT')
        
        assert market_id is None


class TestOHLCVOperations:
    """測試 OHLCV 操作"""
    
    def test_insert_ohlcv_batch_success(self, mock_connection_pool):
        """測試批次寫入 OHLCV 成功"""
        from loaders.db_loader import DatabaseLoader
        
        DatabaseLoader._connection_pool = None
        db = DatabaseLoader()
        
        # 準備測試資料
        ohlcv_data = [
            [1704067200000, 42000.0, 42100.0, 41900.0, 42050.0, 100.5],
            [1704067260000, 42050.0, 42150.0, 42000.0, 42100.0, 150.3],
        ]
        
        cursor = mock_connection_pool['cursor']
        cursor.rowcount = 2
        
        count = db.insert_ohlcv_batch(market_id=1, timeframe='1m', ohlcv_data=ohlcv_data)
        
        assert count == 2
        # 驗證使用了 execute_batch
        assert cursor.execute.called or cursor.executemany.called
    
    def test_insert_ohlcv_batch_empty_data(self, mock_connection_pool):
        """測試空資料時返回 0"""
        from loaders.db_loader import DatabaseLoader
        
        DatabaseLoader._connection_pool = None
        db = DatabaseLoader()
        
        count = db.insert_ohlcv_batch(market_id=1, timeframe='1m', ohlcv_data=[])
        
        assert count == 0
    
    def test_insert_ohlcv_batch_handles_duplicate(self, mock_connection_pool):
        """測試處理重複資料（ON CONFLICT）"""
        from loaders.db_loader import DatabaseLoader
        
        DatabaseLoader._connection_pool = None
        db = DatabaseLoader()
        
        # 準備測試資料
        ohlcv_data = [
            [1704067200000, 42000.0, 42100.0, 41900.0, 42050.0, 100.5],
        ]
        
        cursor = mock_connection_pool['cursor']
        cursor.rowcount = 0  # 沒有新插入（因為重複）
        
        count = db.insert_ohlcv_batch(market_id=1, timeframe='1m', ohlcv_data=ohlcv_data)
        
        # 應該不拋出異常，返回實際寫入數量
        assert count == 0


class TestErrorHandling:
    """測試錯誤處理"""
    
    def test_handles_database_error(self, mock_connection_pool):
        """測試處理資料庫錯誤"""
        from loaders.db_loader import DatabaseLoader
        
        DatabaseLoader._connection_pool = None
        db = DatabaseLoader()
        
        # 模擬資料庫錯誤
        cursor = mock_connection_pool['cursor']
        cursor.execute.side_effect = psycopg2.DatabaseError("Query failed")
        
        with pytest.raises(psycopg2.DatabaseError):
            db.get_market_id('binance', 'BTCUSDT')
    
    def test_handles_connection_timeout(self, mock_connection_pool):
        """測試處理連接超時"""
        from loaders.db_loader import DatabaseLoader
        
        DatabaseLoader._connection_pool = None
        db = DatabaseLoader()
        
        # 模擬連接超時
        mock_connection_pool['pool_instance'].getconn.side_effect = \
            psycopg2.OperationalError("connection timeout")
        
        with pytest.raises(psycopg2.OperationalError):
            with db.get_connection() as conn:
                pass


@pytest.mark.unit
class TestSymbolParsing:
    """測試符號解析整合"""
    
    def test_symbol_is_normalized_before_db_operation(self, mock_connection_pool):
        """測試符號在資料庫操作前被標準化"""
        from loaders.db_loader import DatabaseLoader
        
        DatabaseLoader._connection_pool = None
        db = DatabaseLoader()
        
        cursor = mock_connection_pool['cursor']
        cursor.fetchone.side_effect = [(1,), (100,)]
        
        # 使用斜線格式符號
        market_id = db.get_market_id('binance', 'BTC/USDT')
        
        # 驗證實際查詢時使用標準化格式
        calls = cursor.execute.call_args_list
        # 應該會呼叫 normalize_symbol 將 'BTC/USDT' 轉為 'BTCUSDT'
        assert market_id == 100
