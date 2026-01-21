"""
CollectorOrchestrator

職責：管理所有連接器與收集器資源，作為任務執行的資源中心

記憶體優化（v2.5）：
- 所有 Collector 使用 ExchangePool 共享 CCXT 實例
- 預期記憶體使用從 645 MB → 150-200 MB (減少 70%)
"""
from typing import Dict, List
from loguru import logger

from config_loader import CollectorConfig
from connectors.bybit_rest import BybitClient
from connectors.funding_rate_collector import FundingRateCollector
from connectors.open_interest_collector import OpenInterestCollector
from connectors.cryptopanic_collector import CryptoPanicCollector
from connectors.bitinfocharts import BitInfoChartsClient
from connectors.fear_greed_collector import FearGreedIndexCollector
from connectors.fred_collector import FREDCollector
from connectors.farside_etf_collector import FarsideInvestorsETFCollector
from connectors.exchange_pool import ExchangePool
from loaders.db_loader import DatabaseLoader
from validators.data_validator import DataValidator
from metrics_exporter import CollectorMetrics
from schedulers.backfill_scheduler import BackfillScheduler
from quality_checker import DataQualityChecker
from config import settings

class CollectorOrchestrator:
    def __init__(
        self,
        collector_configs: List[CollectorConfig],
        db_loader: DatabaseLoader,
        validator: DataValidator,
        metrics: CollectorMetrics
    ):
        self.collector_configs = collector_configs
        self.db = db_loader
        self.validator = validator
        self.metrics = metrics
        
        # 初始化維護工具
        self.backfill_scheduler = BackfillScheduler(db_conn=self.db.conn)
        self.quality_checker = DataQualityChecker(
            db_loader=self.db,
            validator=self.validator,
            backfill_scheduler=self.backfill_scheduler
        )
        
        # 連接器與收集器
        self.connectors = {}
        self.funding_rate_collectors = {}
        self.open_interest_collectors = {}
        self.news_collector = CryptoPanicCollector()
        self.rich_list_collector = BitInfoChartsClient()
        
        # Phase 1: Macro Indicators Collectors
        self.fear_greed_collector = FearGreedIndexCollector()
        self.fred_collector = FREDCollector(api_key=settings.fred_api_key if settings.fred_api_key else None)
        self.etf_flows_collector = FarsideInvestorsETFCollector(use_selenium=True)
        
        self._init_connectors()
        self._init_derivatives_collectors()
        self._log_memory_optimization()

    def _init_connectors(self):
        """
        初始化 REST Connectors
        """
        exchanges = set(cfg.exchange.name for cfg in self.collector_configs)
        for name in exchanges:
            cfg = next(c for c in self.collector_configs if c.exchange.name == name)
            if name == 'bybit':
                self.connectors['bybit'] = BybitClient(
                    api_key=cfg.exchange.api_key, 
                    api_secret=cfg.exchange.api_secret
                )
        logger.info(f"Initialized REST connectors for: {list(self.connectors.keys())}")

    def _init_derivatives_collectors(self):
        """
        初始化衍生品收集器（Funding Rate & Open Interest）
        
        記憶體優化：所有 Derivatives Collectors 共享 ExchangePool 實例
        """
        exchanges = set(cfg.exchange.name for cfg in self.collector_configs)
        for name in exchanges:
            cfg = next((c for c in self.collector_configs if c.exchange.name == name), None)
            api_key = cfg.exchange.api_key if cfg else None
            api_secret = cfg.exchange.api_secret if cfg else None
            
            # ✅ 這些 Collectors 內部會自動使用 ExchangePool
            self.funding_rate_collectors[name] = FundingRateCollector(
                exchange_name=name, 
                api_key=api_key, 
                api_secret=api_secret
            )
            self.open_interest_collectors[name] = OpenInterestCollector(
                exchange_name=name, 
                api_key=api_key, 
                api_secret=api_secret
            )
        
        logger.info(f"Initialized derivatives collectors for: {list(self.funding_rate_collectors.keys())}")
    
    def _log_memory_optimization(self):
        """記錄記憶體優化統計資訊"""
        pool = ExchangePool()
        stats = pool.get_stats()
        
        logger.info(
            f"📊 ExchangePool Statistics:\n"
            f"  - Total CCXT instances: {stats['total_exchanges']}\n"
            f"  - Exchanges: {stats['exchanges']}\n"
            f"  - Estimated memory saved: {stats['estimated_memory_saved_mb']} MB\n"
            f"  - Optimization ratio: {stats['optimization_ratio']}"
        )