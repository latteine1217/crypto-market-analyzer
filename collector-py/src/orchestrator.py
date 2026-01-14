"""
CollectorOrchestrator
職責：協調所有交易所連接器的資料收集工作

提取自 main.py 以簡化主程式結構
遵循單一職責原則：只負責資料收集的協調與執行
"""
from typing import Dict, List, Optional
from datetime import timedelta
from loguru import logger
import time

from config_loader import CollectorConfig
from connectors.binance_rest import BinanceRESTConnector
from connectors.okx_rest import OKXRESTConnector
from connectors.funding_rate_collector import FundingRateCollector
from connectors.open_interest_collector import OpenInterestCollector
from loaders.db_loader import DatabaseLoader
from validators.data_validator import DataValidator
from error_handler import (
    retry_with_backoff,
    RetryConfig,
    ErrorClassifier
)
from metrics_exporter import CollectorMetrics


class CollectorOrchestrator:
    """
    資料收集協調器
    
    職責：
    - 管理所有交易所連接器
    - 協調 OHLCV、資金費率、未平倉合約資料收集
    - 處理資料驗證與寫入
    """
    
    def __init__(
        self,
        collector_configs: List[CollectorConfig],
        db_loader: DatabaseLoader,
        validator: DataValidator,
        metrics: CollectorMetrics
    ):
        """
        初始化協調器
        
        Args:
            collector_configs: 收集器配置列表
            db_loader: 資料庫載入器
            validator: 資料驗證器
            metrics: Metrics 收集器
        """
        self.collector_configs = collector_configs
        self.db = db_loader
        self.validator = validator
        self.metrics = metrics
        
        # 初始化連接器
        self.connectors: Dict[str, any] = {}
        self.funding_rate_collectors: Dict[str, FundingRateCollector] = {}
        self.open_interest_collectors: Dict[str, OpenInterestCollector] = {}
        
        self._init_connectors()
        self._init_derivatives_collectors()
        
        logger.info(
            f"CollectorOrchestrator initialized with {len(self.collector_configs)} configs, "
            f"{len(self.connectors)} connectors"
        )
    
    def _init_connectors(self):
        """初始化交易所連接器"""
        # 取得所有唯一的交易所
        exchanges = set(cfg.exchange.name for cfg in self.collector_configs)
        
        for exchange_name in exchanges:
            if exchange_name == 'binance':
                binance_cfg = next(
                    cfg for cfg in self.collector_configs
                    if cfg.exchange.name == 'binance'
                )
                self.connectors['binance'] = BinanceRESTConnector(
                    api_key=binance_cfg.exchange.api_key,
                    api_secret=binance_cfg.exchange.api_secret
                )
                logger.info("Initialized Binance REST connector")
            
            elif exchange_name == 'okx':
                okx_cfg = next(
                    cfg for cfg in self.collector_configs
                    if cfg.exchange.name == 'okx'
                )
                self.connectors['okx'] = OKXRESTConnector(
                    api_key=okx_cfg.exchange.api_key,
                    api_secret=okx_cfg.exchange.api_secret,
                    passphrase=okx_cfg.exchange.passphrase
                )
                logger.info("Initialized OKX REST connector")
            
            # TODO: 支援更多交易所（bybit, etc.）
    
    def _init_derivatives_collectors(self):
        """初始化衍生品資料收集器（資金費率、未平倉合約）"""
        for config in self.collector_configs:
            exchange_name = config.exchange.name
            
            # 初始化 Funding Rate Collector
            if exchange_name not in self.funding_rate_collectors:
                if exchange_name == 'binance':
                    connector = self.connectors.get('binance')
                    if connector:
                        self.funding_rate_collectors['binance'] = FundingRateCollector(
                            exchange_name='binance',
                            connector=connector,
                            db=self.db,
                            metrics=self.metrics
                        )
                elif exchange_name == 'okx':
                    connector = self.connectors.get('okx')
                    if connector:
                        self.funding_rate_collectors['okx'] = FundingRateCollector(
                            exchange_name='okx',
                            connector=connector,
                            db=self.db,
                            metrics=self.metrics
                        )
            
            # 初始化 Open Interest Collector
            if exchange_name not in self.open_interest_collectors:
                if exchange_name == 'binance':
                    connector = self.connectors.get('binance')
                    if connector:
                        self.open_interest_collectors['binance'] = OpenInterestCollector(
                            exchange_name='binance',
                            connector=connector,
                            db=self.db,
                            metrics=self.metrics
                        )
                elif exchange_name == 'okx':
                    connector = self.connectors.get('okx')
                    if connector:
                        self.open_interest_collectors['okx'] = OpenInterestCollector(
                            exchange_name='okx',
                            connector=connector,
                            db=self.db,
                            metrics=self.metrics
                        )
        
        logger.info(
            f"Initialized derivatives collectors: "
            f"{len(self.funding_rate_collectors)} funding rate, "
            f"{len(self.open_interest_collectors)} open interest"
        )
    
    def collect_ohlcv(self, config: CollectorConfig):
        """
        收集 OHLCV 資料
        
        Args:
            config: Collector 配置
        """
        exchange_name = config.exchange.name
        symbol = f"{config.symbol.base}/{config.symbol.quote}"
        timeframe = config.timeframe
        
        logger.info(f"=== Collecting {exchange_name.upper()} {symbol} {timeframe} OHLCV ===")
        
        try:
            # 取得 market_id
            market_id = self.db.get_market_id(exchange_name, symbol)
            if not market_id:
                logger.error(f"Failed to get market_id for {exchange_name}/{symbol}")
                return
            
            # 檢查最新數據時間
            latest_time = self.db.get_latest_ohlcv_time(market_id, timeframe)
            if latest_time:
                logger.info(f"Latest data in DB: {latest_time}")
                lookback_minutes = config.mode.periodic.lookback_minutes
                since_time = latest_time - timedelta(minutes=lookback_minutes)
                since = int(since_time.timestamp() * 1000)
            else:
                logger.info("No existing data, fetching recent candles")
                since = None
            
            # 取得連接器
            connector = self.connectors.get(exchange_name)
            if not connector:
                logger.error(f"Connector not found for {exchange_name}")
                return
            
            # 使用重試機制抓取資料
            retry_config = RetryConfig(
                max_retries=config.request.max_retries,
                initial_delay=config.request.retry_delay,
                backoff_factor=config.request.backoff_factor
            )
            
            @retry_with_backoff(
                config=retry_config,
                exchange_name=exchange_name,
                endpoint='fetch_ohlcv'
            )
            def fetch_with_retry():
                start_time = time.time()
                try:
                    result = connector.fetch_ohlcv(
                        symbol=symbol,
                        timeframe=timeframe,
                        since=since,
                        limit=1000
                    )
                    duration = time.time() - start_time
                    self.metrics.record_api_request(
                        exchange=exchange_name,
                        endpoint='fetch_ohlcv',
                        status='success',
                        duration=duration
                    )
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    self.metrics.record_api_request(
                        exchange=exchange_name,
                        endpoint='fetch_ohlcv',
                        status='failed',
                        duration=duration
                    )
                    error_class = ErrorClassifier.classify_error(e)
                    error_type = error_class.error_type.value if error_class else 'unknown'
                    self.metrics.record_api_error(
                        exchange=exchange_name,
                        endpoint='fetch_ohlcv',
                        error_type=error_type
                    )
                    raise
            
            ohlcv = fetch_with_retry()
            
            if not ohlcv:
                logger.warning("No new data fetched")
                return
            
            # 資料驗證（如果啟用）
            if config.validation.enabled:
                validation_result = self.validator.validate_ohlcv_batch(
                    ohlcv, timeframe
                )
                
                if not validation_result['valid']:
                    logger.warning(
                        f"Validation failed: {validation_result.get('message', 'Unknown error')}"
                    )
                    if not config.validation.skip_on_error:
                        logger.error("Skipping insert due to validation failure")
                        return
            
            # 寫入資料庫
            inserted_count = self.db.insert_ohlcv_batch(
                market_id=market_id,
                timeframe=timeframe,
                ohlcv_data=ohlcv
            )
            
            logger.info(
                f"✓ Inserted {inserted_count}/{len(ohlcv)} candles for "
                f"{exchange_name.upper()} {symbol} {timeframe}"
            )
            
            # 記錄 metrics
            self.metrics.record_data_collected(
                exchange=exchange_name,
                data_type='ohlcv',
                count=inserted_count
            )
            
        except Exception as e:
            logger.error(f"Failed to collect OHLCV for {exchange_name} {symbol}: {e}")
            raise
    
    def run_collection_cycle(self):
        """執行一次完整的資料收集循環"""
        logger.info("=== Starting Collection Cycle ===")
        
        for config in self.collector_configs:
            try:
                self.collect_ohlcv(config)
            except Exception as e:
                logger.error(f"Collection failed for {config.exchange.name} {config.symbol}: {e}")
        
        logger.info("=== Collection Cycle Completed ===")
    
    def run_funding_rate_collection(self):
        """執行資金費率收集"""
        logger.info("=== Starting Funding Rate Collection ===")
        
        for exchange_name, collector in self.funding_rate_collectors.items():
            try:
                # 取得該交易所的所有交易對
                symbols = [
                    f"{cfg.symbol.base}/{cfg.symbol.quote}"
                    for cfg in self.collector_configs
                    if cfg.exchange.name == exchange_name
                ]
                
                for symbol in symbols:
                    try:
                        collector.collect_funding_rate(symbol)
                    except Exception as e:
                        logger.error(
                            f"Failed to collect funding rate for {exchange_name} {symbol}: {e}"
                        )
            except Exception as e:
                logger.error(f"Funding rate collection failed for {exchange_name}: {e}")
        
        logger.info("=== Funding Rate Collection Completed ===")
    
    def run_open_interest_collection(self):
        """執行未平倉合約收集"""
        logger.info("=== Starting Open Interest Collection ===")
        
        for exchange_name, collector in self.open_interest_collectors.items():
            try:
                # 取得該交易所的所有交易對
                symbols = [
                    f"{cfg.symbol.base}/{cfg.symbol.quote}"
                    for cfg in self.collector_configs
                    if cfg.exchange.name == exchange_name
                ]
                
                for symbol in symbols:
                    try:
                        collector.collect_open_interest(symbol)
                    except Exception as e:
                        logger.error(
                            f"Failed to collect open interest for {exchange_name} {symbol}: {e}"
                        )
            except Exception as e:
                logger.error(f"Open interest collection failed for {exchange_name}: {e}")
        
        logger.info("=== Open Interest Collection Completed ===")
