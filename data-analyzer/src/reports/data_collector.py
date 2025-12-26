"""
Report Data Collector - 報表資料收集器

職責：
1. 從資料庫收集資料品質摘要
2. 從檔案系統讀取回測結果
3. 收集模型訓練結果
4. 統一資料格式供報表生成器使用
"""
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
from loguru import logger
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import json


class ReportDataCollector:
    """報表資料收集器"""

    def __init__(
        self,
        db_config: Optional[Dict] = None,
        results_dir: str = "results"
    ):
        """
        初始化資料收集器

        Args:
            db_config: 資料庫配置字典
            results_dir: 回測結果目錄
        """
        self.db_config = db_config or self._get_default_db_config()
        self.results_dir = Path(results_dir)
        self.conn = None

        # 嘗試連接資料庫
        try:
            self.conn = self._connect_db()
            logger.info("✓ 資料庫連接成功")
        except Exception as e:
            logger.warning(f"資料庫連接失敗：{e}")
            logger.warning("將僅使用檔案系統資料")

    def collect_quality_summary(
        self,
        start_date: datetime,
        end_date: datetime,
        markets: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        收集資料品質摘要

        Args:
            start_date: 起始日期
            end_date: 結束日期
            markets: 市場列表（可選）

        Returns:
            資料品質摘要列表
        """
        if self.conn is None:
            logger.warning("無資料庫連接，返回空品質摘要")
            return []

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                if markets:
                    # 先查詢 market_id
                    market_ids = self._get_market_ids(markets)
                    if not market_ids:
                        logger.warning(f"找不到市場：{markets}")
                        return []

                    cur.execute(
                        """
                        SELECT
                            dqs.*,
                            m.symbol,
                            e.name AS exchange
                        FROM data_quality_summary dqs
                        JOIN markets m ON dqs.market_id = m.id
                        JOIN exchanges e ON m.exchange_id = e.id
                        WHERE dqs.check_time >= %s
                          AND dqs.check_time < %s
                          AND dqs.market_id = ANY(%s)
                        ORDER BY dqs.check_time DESC
                        """,
                        (start_date, end_date, market_ids)
                    )
                else:
                    cur.execute(
                        """
                        SELECT
                            dqs.*,
                            m.symbol,
                            e.name AS exchange
                        FROM data_quality_summary dqs
                        JOIN markets m ON dqs.market_id = m.id
                        JOIN exchanges e ON m.exchange_id = e.id
                        WHERE dqs.check_time >= %s
                          AND dqs.check_time < %s
                        ORDER BY dqs.check_time DESC
                        """,
                        (start_date, end_date)
                    )

                rows = cur.fetchall()

            # 轉換為列表字典
            quality_summary = []
            for row in rows:
                record = dict(row)
                # 轉換時間戳為字串
                for key in ['check_time', 'time_range_start', 'time_range_end', 'created_at']:
                    if key in record and record[key]:
                        record[key] = record[key].isoformat()
                quality_summary.append(record)

            logger.info(f"收集到 {len(quality_summary)} 筆品質摘要")
            return quality_summary

        except Exception as e:
            logger.error(f"收集品質摘要失敗：{e}")
            return []

    def collect_backtest_results(
        self,
        strategies: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """
        收集回測結果

        Args:
            strategies: 策略列表（可選）
            start_date: 起始日期（可選，用於過濾）
            end_date: 結束日期（可選，用於過濾）

        Returns:
            回測結果列表
        """
        backtest_dir = self.results_dir / "backtest_reports"

        if not backtest_dir.exists():
            logger.warning(f"回測結果目錄不存在：{backtest_dir}")
            return []

        results = []

        # 遍歷策略目錄
        for strategy_dir in backtest_dir.iterdir():
            if not strategy_dir.is_dir():
                continue

            strategy_name = strategy_dir.name

            # 如果指定了策略列表，只收集指定的策略
            if strategies and strategy_name not in strategies:
                continue

            # 查找 JSON 結果檔案（如果存在）
            json_file = strategy_dir / f"{strategy_name}_results.json"
            if json_file.exists():
                try:
                    with open(json_file, 'r') as f:
                        result_data = json.load(f)
                    results.append(result_data)
                    logger.debug(f"載入 JSON 結果：{json_file}")
                    continue
                except Exception as e:
                    logger.warning(f"讀取 JSON 失敗：{json_file}，錯誤：{e}")

            # 如果沒有 JSON，從圖表推斷基本資訊
            png_files = list(strategy_dir.glob("*.png"))
            if png_files:
                results.append({
                    'strategy_name': strategy_name,
                    'has_visualizations': True,
                    'visualization_files': [str(f) for f in png_files],
                    'metrics': None,  # 無結構化資料
                })
                logger.debug(f"找到視覺化檔案：{strategy_name}")

        logger.info(f"收集到 {len(results)} 個策略的回測結果")
        return results

    def collect_model_results(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """
        收集模型訓練結果

        Args:
            start_date: 起始日期（可選）
            end_date: 結束日期（可選）

        Returns:
            模型結果列表
        """
        try:
            # 動態導入 ModelRegistry
            import sys
            from pathlib import Path

            # 加入模型模組路徑
            models_path = Path(__file__).parent.parent / "models"
            if str(models_path) not in sys.path:
                sys.path.insert(0, str(models_path))

            from model_registry import ModelRegistry

            registry = ModelRegistry()

            if start_date and end_date:
                # 獲取時間範圍內的模型
                models = registry.get_models_in_period(start_date, end_date)
                logger.info(f"收集到 {len(models)} 個模型結果（{start_date} ~ {end_date}）")
            else:
                # 獲取最新的模型
                models = registry.get_latest_models(limit=10)
                logger.info(f"收集到最新 {len(models)} 個模型結果")

            return models

        except Exception as e:
            logger.warning(f"模型結果收集失敗：{e}")
            logger.debug("如果尚未註冊任何模型，這是正常的")
            return []

    def get_quality_statistics(
        self,
        start_date: datetime,
        end_date: datetime,
        markets: Optional[List[str]] = None
    ) -> Dict:
        """
        獲取資料品質統計摘要

        Args:
            start_date: 起始日期
            end_date: 結束日期
            markets: 市場列表（可選）

        Returns:
            統計摘要字典
        """
        if self.conn is None:
            return {}

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                market_filter = ""
                params = [start_date, end_date]

                if markets:
                    market_ids = self._get_market_ids(markets)
                    if market_ids:
                        market_filter = "AND dqs.market_id = ANY(%s)"
                        params.append(market_ids)

                cur.execute(
                    f"""
                    SELECT
                        COUNT(*) AS total_checks,
                        AVG(quality_score) AS avg_quality_score,
                        MIN(quality_score) AS min_quality_score,
                        MAX(quality_score) AS max_quality_score,
                        SUM(CASE WHEN is_valid = FALSE THEN 1 ELSE 0 END) AS failed_checks,
                        SUM(missing_count) AS total_missing,
                        SUM(out_of_order_count) AS total_out_of_order,
                        SUM(price_jump_count) AS total_price_jumps
                    FROM data_quality_summary dqs
                    WHERE check_time >= %s
                      AND check_time < %s
                      {market_filter}
                    """,
                    params
                )

                row = cur.fetchone()

            if row:
                return {
                    'total_checks': row['total_checks'] or 0,
                    'avg_quality_score': float(row['avg_quality_score'] or 0),
                    'min_quality_score': float(row['min_quality_score'] or 0),
                    'max_quality_score': float(row['max_quality_score'] or 0),
                    'failed_checks': row['failed_checks'] or 0,
                    'total_missing': row['total_missing'] or 0,
                    'total_out_of_order': row['total_out_of_order'] or 0,
                    'total_price_jumps': row['total_price_jumps'] or 0,
                }
            else:
                return {}

        except Exception as e:
            logger.error(f"獲取品質統計失敗：{e}")
            return {}

    def _get_market_ids(self, symbols: List[str]) -> List[int]:
        """根據 symbol 獲取 market_id"""
        if self.conn is None:
            return []

        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id
                    FROM markets
                    WHERE symbol = ANY(%s)
                    """,
                    (symbols,)
                )
                rows = cur.fetchall()
                return [row[0] for row in rows]

        except Exception as e:
            logger.error(f"獲取 market_id 失敗：{e}")
            return []

    def _connect_db(self):
        """連接資料庫"""
        return psycopg2.connect(
            host=self.db_config.get('host', 'localhost'),
            port=self.db_config.get('port', 5432),
            database=self.db_config.get('database', 'crypto_market'),
            user=self.db_config.get('user', 'postgres'),
            password=self.db_config.get('password', '')
        )

    def _get_default_db_config(self) -> Dict:
        """獲取預設資料庫配置"""
        return {
            'host': 'localhost',
            'port': 5432,
            'database': 'crypto_market',
            'user': 'postgres',
            'password': ''  # 應從環境變數或配置檔讀取
        }

    def close(self):
        """關閉資料庫連接"""
        if self.conn:
            self.conn.close()
            logger.info("資料庫連接已關閉")


# 範例用法
if __name__ == "__main__":
    from datetime import timedelta

    collector = ReportDataCollector()

    # 測試收集資料品質摘要
    end_date = datetime.now()
    start_date = end_date - timedelta(hours=24)

    quality_summary = collector.collect_quality_summary(
        start_date=start_date,
        end_date=end_date,
        markets=['BTC/USDT']
    )

    print(f"收集到 {len(quality_summary)} 筆品質摘要")

    # 測試收集回測結果
    backtest_results = collector.collect_backtest_results(
        strategies=['RSI', 'MA_Cross']
    )

    print(f"收集到 {len(backtest_results)} 個策略結果")

    # 測試品質統計
    stats = collector.get_quality_statistics(
        start_date=start_date,
        end_date=end_date
    )

    print(f"品質統計：{stats}")

    collector.close()
