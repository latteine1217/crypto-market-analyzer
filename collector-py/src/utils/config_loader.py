"""
配置載入工具

負責載入 YAML 配置文件並處理環境變數替換
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any
import re


def expand_env_vars(value: Any) -> Any:
    """
    遞歸展開環境變數

    支持格式: ${VAR_NAME:-default_value}

    Args:
        value: 待處理的值（可能是 str, dict, list 等）

    Returns:
        展開後的值
    """
    if isinstance(value, str):
        # 匹配 ${VAR_NAME} 或 ${VAR_NAME:-default} 格式
        pattern = r'\$\{([^}:]+)(?::-(.*?))?\}'

        def replace_match(match):
            var_name = match.group(1)
            default_value = match.group(2) if match.group(2) is not None else ''
            return os.environ.get(var_name, default_value)

        return re.sub(pattern, replace_match, value)

    elif isinstance(value, dict):
        return {k: expand_env_vars(v) for k, v in value.items()}

    elif isinstance(value, list):
        return [expand_env_vars(item) for item in value]

    else:
        return value


def load_whale_tracker_config(config_path: str = None) -> Dict[str, Any]:
    """
    載入巨鯨追蹤配置

    Args:
        config_path: 配置文件路徑（默認為 configs/whale_tracker.yml）

    Returns:
        配置字典
    """
    if config_path is None:
        # 默認路徑：專案根目錄 / configs / whale_tracker.yml
        # Docker: /app/src/utils/config_loader.py -> /app/configs/whale_tracker.yml
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / 'configs' / 'whale_tracker.yml'

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 展開環境變數
    config = expand_env_vars(config)

    return config


def get_blockchain_config(blockchain: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    獲取特定區塊鏈的配置

    Args:
        blockchain: 區塊鏈名稱（BTC, ETH, BSC, TRX）
        config: 完整配置字典

    Returns:
        該區塊鏈的配置字典
    """
    blockchain_lower = blockchain.lower()

    # 區塊鏈名稱映射 (縮寫 -> 完整名稱)
    blockchain_name_mapping = {
        'eth': 'ethereum',
        'btc': 'bitcoin',
        'bsc': 'bsc',
        'trx': 'tron',
    }

    # 基礎配置
    endpoint_name = blockchain_name_mapping.get(blockchain_lower, blockchain_lower)
    endpoint_config = config.get('endpoints', {}).get(endpoint_name, {})

    # 門檻配置
    thresholds = config.get('thresholds', {})
    anomaly_thresholds = config.get('anomaly_thresholds', {})

    # API key
    api_keys = config.get('api_keys', {})

    # 根據區塊鏈類型選擇正確的 API key
    api_key_mapping = {
        'eth': 'etherscan',
        'ethereum': 'etherscan',
        'bsc': 'bscscan',
        'trx': 'tronscan',
        'tron': 'tronscan',
        'btc': None,  # Bitcoin 不需要 API key
        'bitcoin': None,
    }

    api_key_name = api_key_mapping.get(blockchain_lower, f'{blockchain_lower}scan')
    api_key = api_keys.get(api_key_name) if api_key_name else None

    # 合併配置
    blockchain_config = {
        'blockchain': blockchain.upper(),
        'api_url': endpoint_config.get('api_url', ''),
        'ws_url': endpoint_config.get('ws_url'),
        'rate_limit': endpoint_config.get('rate_limit', 5),
        'timeout': endpoint_config.get('timeout', 30),
        'whale_threshold': thresholds.get(blockchain.upper(), {}),
        'anomaly_threshold': anomaly_thresholds.get(blockchain.upper(), {}),
        'api_key': api_key,
    }

    # 處理特殊配置（如 Bitcoin 的多個 API）
    if blockchain_lower == 'bitcoin':
        blockchain_config['blockchair_url'] = endpoint_config.get('blockchair_url', '')

    if blockchain_lower == 'tron':
        blockchain_config['grid_url'] = endpoint_config.get('grid_url', '')

    return blockchain_config


if __name__ == '__main__':
    from loguru import logger
    
    # 測試配置載入
    config = load_whale_tracker_config()

    logger.info("=== 完整配置 ===")
    logger.info(f"API Keys: {config.get('api_keys', {})}")
    logger.info(f"Thresholds: {config.get('thresholds', {})}")

    logger.info("=== Ethereum 配置 ===")
    eth_config = get_blockchain_config('ETH', config)
    for key, value in eth_config.items():
        logger.info(f"{key}: {value}")

    logger.info("=== Bitcoin 配置 ===")
    btc_config = get_blockchain_config('BTC', config)
    for key, value in btc_config.items():
        logger.info(f"{key}: {value}")
