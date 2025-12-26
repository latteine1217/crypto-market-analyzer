"""
Model Registry - 模型註冊與結果追蹤

職責：
1. 記錄模型訓練結果
2. 保存模型 metadata
3. 提供模型查詢介面
"""
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import json
from loguru import logger
import pandas as pd


class ModelRegistry:
    """模型註冊表"""

    def __init__(self, registry_dir: str = "models/registry"):
        """
        初始化模型註冊表

        Args:
            registry_dir: 註冊表目錄
        """
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.registry_dir / "model_index.json"

        # 載入或創建索引
        self.index = self._load_index()

    def register_model(
        self,
        model_name: str,
        model_type: str,
        model_version: str,
        training_metrics: Dict,
        model_config: Dict,
        training_data_info: Dict,
        model_path: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        註冊模型訓練結果

        Args:
            model_name: 模型名稱 (如 'LSTM_Price_Forecast')
            model_type: 模型類型 (如 'lstm', 'xgboost', 'arima')
            model_version: 版本號 (如 'v1.0.0', '20241226_001')
            training_metrics: 訓練指標 (MSE, MAE, R2 等)
            model_config: 模型配置
            training_data_info: 訓練資料資訊
            model_path: 模型檔案路徑
            metadata: 額外 metadata

        Returns:
            model_id
        """
        # 生成 model_id
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        model_id = f"{model_name}_{model_version}_{timestamp}"

        # 建立記錄
        record = {
            'model_id': model_id,
            'model_name': model_name,
            'model_type': model_type,
            'model_version': model_version,
            'registered_at': datetime.now().isoformat(),
            'training_metrics': training_metrics,
            'model_config': model_config,
            'training_data_info': training_data_info,
            'model_path': model_path,
            'metadata': metadata or {},
        }

        # 保存詳細記錄
        record_path = self.registry_dir / f"{model_id}.json"
        with open(record_path, 'w', encoding='utf-8') as f:
            json.dump(record, f, indent=2, ensure_ascii=False)

        # 更新索引
        self.index.append({
            'model_id': model_id,
            'model_name': model_name,
            'model_type': model_type,
            'model_version': model_version,
            'registered_at': record['registered_at'],
            'record_path': str(record_path),
        })
        self._save_index()

        logger.info(f"✓ 模型已註冊：{model_id}")
        return model_id

    def get_model_record(self, model_id: str) -> Optional[Dict]:
        """獲取模型記錄"""
        record_path = self.registry_dir / f"{model_id}.json"
        if not record_path.exists():
            logger.warning(f"模型記錄不存在：{model_id}")
            return None

        with open(record_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_latest_models(
        self,
        model_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        獲取最新的模型記錄

        Args:
            model_type: 模型類型過濾
            limit: 返回數量限制

        Returns:
            模型記錄列表
        """
        filtered_index = self.index

        if model_type:
            filtered_index = [
                record for record in filtered_index
                if record.get('model_type') == model_type
            ]

        # 按註冊時間排序
        sorted_index = sorted(
            filtered_index,
            key=lambda x: x.get('registered_at', ''),
            reverse=True
        )

        # 載入完整記錄
        results = []
        for idx_record in sorted_index[:limit]:
            full_record = self.get_model_record(idx_record['model_id'])
            if full_record:
                results.append(full_record)

        return results

    def get_models_in_period(
        self,
        start_date: datetime,
        end_date: datetime,
        model_type: Optional[str] = None
    ) -> List[Dict]:
        """
        獲取時間範圍內的模型記錄

        Args:
            start_date: 起始日期
            end_date: 結束日期
            model_type: 模型類型過濾

        Returns:
            模型記錄列表
        """
        results = []

        for idx_record in self.index:
            registered_at = datetime.fromisoformat(idx_record['registered_at'])

            if start_date <= registered_at <= end_date:
                if model_type and idx_record.get('model_type') != model_type:
                    continue

                full_record = self.get_model_record(idx_record['model_id'])
                if full_record:
                    results.append(full_record)

        return results

    def get_model_summary_df(self) -> pd.DataFrame:
        """獲取模型摘要 DataFrame"""
        summaries = []

        for idx_record in self.index:
            full_record = self.get_model_record(idx_record['model_id'])
            if not full_record:
                continue

            metrics = full_record.get('training_metrics', {})

            summary = {
                'model_id': full_record['model_id'],
                'model_name': full_record['model_name'],
                'model_type': full_record['model_type'],
                'model_version': full_record['model_version'],
                'registered_at': full_record['registered_at'],
                **metrics  # 展開所有訓練指標
            }

            summaries.append(summary)

        return pd.DataFrame(summaries)

    def _load_index(self) -> List[Dict]:
        """載入索引"""
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def _save_index(self):
        """保存索引"""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, indent=2, ensure_ascii=False)


# 範例用法
if __name__ == "__main__":
    registry = ModelRegistry()

    # 註冊一個 LSTM 模型
    model_id = registry.register_model(
        model_name="LSTM_Price_Forecast",
        model_type="lstm",
        model_version="v1.0.0",
        training_metrics={
            'mse': 0.0123,
            'mae': 0.089,
            'r2_score': 0.85,
            'val_loss': 0.0145,
        },
        model_config={
            'hidden_size': 128,
            'num_layers': 2,
            'dropout': 0.2,
            'learning_rate': 0.001,
        },
        training_data_info={
            'symbol': 'BTC/USDT',
            'timeframe': '1m',
            'start_date': '2024-01-01',
            'end_date': '2024-12-26',
            'train_samples': 50000,
            'val_samples': 10000,
        },
        model_path="models/saved/lstm_btc_20241226.pth",
        metadata={
            'training_duration': 3600,  # seconds
            'gpu_used': 'NVIDIA RTX 4090',
        }
    )

    print(f"模型已註冊：{model_id}")

    # 查詢最新模型
    latest_models = registry.get_latest_models(limit=5)
    print(f"\n最新的 5 個模型：")
    for model in latest_models:
        print(f"  {model['model_id']} - {model['model_name']}")

    # 獲取摘要 DataFrame
    df = registry.get_model_summary_df()
    print(f"\n模型摘要：")
    print(df.head())
