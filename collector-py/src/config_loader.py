"""
配置檔載入器
職責：
1. 載入 YAML 配置檔
2. 支援環境變數替換
3. 驗證配置格式
4. 提供類型安全的配置訪問
"""
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from loguru import logger
import yaml


@dataclass
class ExchangeConfig:
    """交易所配置"""
    name: str
    api_endpoint: str
    api_key: Optional[str] = None
    api_secret: Optional[str] = None


@dataclass
class SymbolConfig:
    """交易對配置"""
    base: str
    quote: str
    exchange_symbol: str


@dataclass
class HistoricalModeConfig:
    """歷史資料模式配置"""
    enabled: bool = True
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    batch_size: int = 1000


@dataclass
class PeriodicModeConfig:
    """定期批次模式配置"""
    enabled: bool = True
    schedule: str = "*/5 * * * *"
    lookback_minutes: int = 10


@dataclass
class RealtimeModeConfig:
    """實時模式配置"""
    enabled: bool = False


@dataclass
class ModeConfig:
    """收集模式配置"""
    historical: HistoricalModeConfig = field(default_factory=HistoricalModeConfig)
    periodic: PeriodicModeConfig = field(default_factory=PeriodicModeConfig)
    realtime: RealtimeModeConfig = field(default_factory=RealtimeModeConfig)


@dataclass
class RequestConfig:
    """API 請求配置"""
    timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 5
    backoff_factor: float = 2.0


@dataclass
class RateLimitConfig:
    """速率限制配置"""
    requests_per_minute: int = 1200
    requests_per_second: int = 20
    weight_per_request: int = 1
    max_weight: int = 1200


@dataclass
class ValidationConfig:
    """資料驗證配置"""
    enabled: bool = True
    checks: List[str] = field(default_factory=lambda: [
        'timestamp_order',
        'no_duplicates',
        'price_range',
        'volume_positive'
    ])


@dataclass
class StorageConfig:
    """儲存配置"""
    target: str = 'timescaledb'
    table: str = 'ohlcv'
    conflict_strategy: str = 'upsert'
    batch_insert: bool = True
    batch_size: int = 100


@dataclass
class ErrorHandlingConfig:
    """錯誤處理配置"""
    on_api_error: str = 'retry'
    on_validation_error: str = 'skip_and_log'
    on_storage_error: str = 'retry'
    max_consecutive_failures: int = 10


@dataclass
class MonitoringConfig:
    """監控配置"""
    log_every_n_batches: int = 10
    metrics: List[str] = field(default_factory=lambda: [
        'rows_inserted',
        'api_calls',
        'api_errors',
        'validation_failures'
    ])


@dataclass
class CollectorConfig:
    """完整的 Collector 配置"""
    name: str
    description: str
    exchange: ExchangeConfig
    symbol: SymbolConfig
    data_type: str
    timeframe: str
    mode: ModeConfig
    request: RequestConfig
    rate_limit: RateLimitConfig
    validation: ValidationConfig
    storage: StorageConfig
    error_handling: ErrorHandlingConfig
    monitoring: MonitoringConfig


class ConfigLoader:
    """配置檔載入器"""

    def __init__(self, config_dir: Optional[Path] = None):
        """
        初始化配置載入器

        Args:
            config_dir: 配置檔目錄，預設為 PROJECT_ROOT/configs/collector
        """
        if config_dir is None:
            # 優先使用環境變數
            import os
            env_config_dir = os.getenv('COLLECTOR_CONFIG_DIR')

            if env_config_dir:
                config_dir = Path(env_config_dir)
            else:
                # 從當前檔案位置推導專案根目錄
                current_file = Path(__file__)
                project_root = current_file.parent.parent.parent
                config_dir = project_root / "configs" / "collector"

        self.config_dir = Path(config_dir)
        if not self.config_dir.exists():
            raise FileNotFoundError(f"配置目錄不存在: {self.config_dir}")

        logger.info(f"ConfigLoader initialized with config_dir: {self.config_dir}")

    @staticmethod
    def _substitute_env_vars(value: Any) -> Any:
        """
        遞迴替換配置中的環境變數

        支援格式：
        - ${VAR_NAME}
        - ${VAR_NAME:default_value}

        Args:
            value: 配置值（可能是字串、字典、列表等）

        Returns:
            替換後的值
        """
        if isinstance(value, str):
            # 匹配 ${VAR_NAME} 或 ${VAR_NAME:default}
            pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'

            def replace(match):
                var_name = match.group(1)
                default_value = match.group(2) if match.group(2) is not None else ''
                return os.environ.get(var_name, default_value)

            return re.sub(pattern, replace, value)

        elif isinstance(value, dict):
            return {k: ConfigLoader._substitute_env_vars(v) for k, v in value.items()}

        elif isinstance(value, list):
            return [ConfigLoader._substitute_env_vars(item) for item in value]

        else:
            return value

    def load_yaml(self, config_file: str) -> Dict[str, Any]:
        """
        載入並解析 YAML 配置檔

        Args:
            config_file: 配置檔名稱（可以是相對於 config_dir 的路徑）

        Returns:
            解析後的配置字典

        Raises:
            FileNotFoundError: 配置檔不存在
            yaml.YAMLError: YAML 解析失敗
        """
        config_path = self.config_dir / config_file

        if not config_path.exists():
            raise FileNotFoundError(f"配置檔不存在: {config_path}")

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f)

            # 替換環境變數
            config = self._substitute_env_vars(raw_config)

            logger.info(f"Successfully loaded config: {config_file}")
            return config

        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML config {config_file}: {e}")
            raise

    def load_collector_config(self, config_file: str) -> CollectorConfig:
        """
        載入並解析 Collector 配置

        Args:
            config_file: 配置檔名稱

        Returns:
            CollectorConfig 對象
        """
        raw = self.load_yaml(config_file)

        # 解析各個配置段
        exchange_config = ExchangeConfig(**raw['exchange'])
        symbol_config = SymbolConfig(**raw['symbol'])

        # 解析 mode 配置
        mode_raw = raw.get('mode', {})
        historical = HistoricalModeConfig(**mode_raw.get('historical', {}))
        periodic = PeriodicModeConfig(**mode_raw.get('periodic', {}))
        realtime = RealtimeModeConfig(**mode_raw.get('realtime', {}))
        mode_config = ModeConfig(
            historical=historical,
            periodic=periodic,
            realtime=realtime
        )

        # 其他配置段
        request_config = RequestConfig(**raw.get('request', {}))
        rate_limit_config = RateLimitConfig(**raw.get('rate_limit', {}))
        validation_config = ValidationConfig(**raw.get('validation', {}))
        storage_config = StorageConfig(**raw.get('storage', {}))
        error_handling_config = ErrorHandlingConfig(**raw.get('error_handling', {}))
        monitoring_config = MonitoringConfig(**raw.get('monitoring', {}))

        return CollectorConfig(
            name=raw['name'],
            description=raw['description'],
            exchange=exchange_config,
            symbol=symbol_config,
            data_type=raw['data_type'],
            timeframe=raw['timeframe'],
            mode=mode_config,
            request=request_config,
            rate_limit=rate_limit_config,
            validation=validation_config,
            storage=storage_config,
            error_handling=error_handling_config,
            monitoring=monitoring_config
        )

    def load_all_collector_configs(self) -> List[CollectorConfig]:
        """
        載入配置目錄下所有的 Collector 配置

        Returns:
            CollectorConfig 列表
        """
        configs = []

        for config_file in self.config_dir.glob("*.yml"):
            try:
                config = self.load_collector_config(config_file.name)
                configs.append(config)
            except Exception as e:
                logger.warning(f"Failed to load config {config_file.name}: {e}")

        logger.info(f"Loaded {len(configs)} collector configs")
        return configs


# 範例用法
if __name__ == "__main__":
    # 測試配置載入
    loader = ConfigLoader()

    # 載入單一配置
    config = loader.load_collector_config("binance_btcusdt_1m.yml")
    print(f"Loaded config: {config.name}")
    print(f"Exchange: {config.exchange.name}")
    print(f"Symbol: {config.symbol.base}/{config.symbol.quote}")
    print(f"Timeframe: {config.timeframe}")
    print(f"Historical mode enabled: {config.mode.historical.enabled}")
    print(f"Request timeout: {config.request.timeout}s")
    print(f"Max retries: {config.request.max_retries}")

    # 載入所有配置
    all_configs = loader.load_all_collector_configs()
    print(f"\nTotal configs loaded: {len(all_configs)}")
    for cfg in all_configs:
        print(f"  - {cfg.name}")
