"""
區塊鏈資料驗證器

負責驗證資料品質、去重、異常檢測
"""
from typing import List, Set, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from loguru import logger

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from connectors.blockchain_base import WhaleTransaction


class BlockchainDataValidator:
    """區塊鏈資料驗證器"""

    def __init__(self):
        """初始化驗證器"""
        self.seen_tx_hashes: Set[str] = set()

    def validate_transaction(
        self,
        tx: WhaleTransaction
    ) -> Tuple[bool, str]:
        """
        驗證單筆交易的有效性

        Args:
            tx: WhaleTransaction 對象

        Returns:
            (is_valid, error_message) 元組
        """
        # 檢查必要欄位
        if not tx.tx_hash:
            return False, "交易哈希為空"

        if not tx.from_address or not tx.to_address:
            return False, "發送或接收地址為空"

        if tx.amount <= 0:
            return False, f"交易金額無效: {tx.amount}"

        if not tx.timestamp:
            return False, "交易時間為空"

        # 檢查時間合理性 (不能在未來，不能太久以前)
        now = datetime.now()
        if tx.timestamp > now + timedelta(minutes=5):
            return False, f"交易時間在未來: {tx.timestamp}"

        # 檢查是否太舊 (超過 1 年)
        if tx.timestamp < now - timedelta(days=365):
            logger.warning(f"交易時間超過 1 年: {tx.timestamp}")

        # 檢查地址格式 (基本檢查)
        if tx.blockchain in ['ETH', 'BSC']:
            if not self._is_valid_eth_address(tx.from_address):
                return False, f"無效的 from_address: {tx.from_address}"
            if not self._is_valid_eth_address(tx.to_address):
                return False, f"無效的 to_address: {tx.to_address}"

        elif tx.blockchain == 'BTC':
            # BTC 地址驗證較複雜,這裡只做基本檢查
            if len(tx.from_address) < 26 or len(tx.from_address) > 62:
                logger.warning(f"可疑的 BTC from_address 長度: {tx.from_address}")

        # 檢查金額合理性
        if tx.amount_usd:
            if tx.amount_usd < 0:
                return False, f"美元價值不能為負: {tx.amount_usd}"

            # 異常大額檢查 (超過 10 億美元視為可疑)
            if tx.amount_usd > 1_000_000_000:
                logger.warning(f"異常大額交易: {tx.amount_usd} USD, {tx.tx_hash}")

        return True, ""

    def _is_valid_eth_address(self, address: str) -> bool:
        """
        檢查是否為有效的以太坊地址格式

        Args:
            address: 地址字串

        Returns:
            是否有效
        """
        if not address:
            return False

        # 基本格式檢查
        if not address.startswith('0x'):
            return False

        if len(address) != 42:  # 0x + 40 hex chars
            return False

        # 檢查是否為合法的十六進制
        try:
            int(address[2:], 16)
            return True
        except ValueError:
            return False

    def deduplicate_transactions(
        self,
        transactions: List[WhaleTransaction]
    ) -> List[WhaleTransaction]:
        """
        去除重複交易 (基於 tx_hash)

        Args:
            transactions: 交易列表

        Returns:
            去重後的交易列表
        """
        unique_txs = []
        seen = set()

        for tx in transactions:
            if tx.tx_hash not in seen:
                seen.add(tx.tx_hash)
                unique_txs.append(tx)

        removed_count = len(transactions) - len(unique_txs)
        if removed_count > 0:
            logger.info(f"去除 {removed_count} 筆重複交易")

        return unique_txs

    def filter_valid_transactions(
        self,
        transactions: List[WhaleTransaction]
    ) -> Tuple[List[WhaleTransaction], List[Tuple[WhaleTransaction, str]]]:
        """
        過濾出有效的交易

        Args:
            transactions: 交易列表

        Returns:
            (valid_txs, invalid_txs_with_reasons) 元組
        """
        valid_txs = []
        invalid_txs = []

        for tx in transactions:
            is_valid, error_msg = self.validate_transaction(tx)

            if is_valid:
                valid_txs.append(tx)
            else:
                invalid_txs.append((tx, error_msg))
                logger.warning(f"無效交易: {tx.tx_hash[:10]}... - {error_msg}")

        logger.info(f"驗證完成: {len(valid_txs)} 筆有效, {len(invalid_txs)} 筆無效")

        return valid_txs, invalid_txs

    def check_time_continuity(
        self,
        transactions: List[WhaleTransaction],
        max_gap_minutes: int = 60
    ) -> List[Tuple[datetime, datetime]]:
        """
        檢查時間序列連續性,找出時間間隔過大的區段

        Args:
            transactions: 交易列表 (應已按時間排序)
            max_gap_minutes: 最大允許間隔 (分鐘)

        Returns:
            時間間隔過大的區段列表 [(gap_start, gap_end), ...]
        """
        if len(transactions) < 2:
            return []

        # 按時間排序
        sorted_txs = sorted(transactions, key=lambda tx: tx.timestamp)

        gaps = []
        max_gap = timedelta(minutes=max_gap_minutes)

        for i in range(len(sorted_txs) - 1):
            current_time = sorted_txs[i].timestamp
            next_time = sorted_txs[i + 1].timestamp

            gap = next_time - current_time

            if gap > max_gap:
                gaps.append((current_time, next_time))
                logger.warning(f"發現時間間隔: {current_time} -> {next_time} ({gap})")

        return gaps

    def detect_price_anomalies(
        self,
        transactions: List[WhaleTransaction],
        threshold_multiplier: float = 10.0
    ) -> List[WhaleTransaction]:
        """
        檢測價格異常的交易

        Args:
            transactions: 交易列表
            threshold_multiplier: 異常倍數閾值

        Returns:
            異常交易列表
        """
        if not transactions:
            return []

        # 計算相同代幣的平均金額
        token_amounts = {}
        for tx in transactions:
            token = tx.token_symbol or tx.blockchain
            if token not in token_amounts:
                token_amounts[token] = []
            token_amounts[token].append(tx.amount)

        # 計算平均值
        token_avg = {
            token: sum(amounts) / len(amounts)
            for token, amounts in token_amounts.items()
        }

        # 找出異常交易
        anomalies = []
        for tx in transactions:
            token = tx.token_symbol or tx.blockchain
            avg = token_avg.get(token, 0)

            if avg > 0 and tx.amount > avg * threshold_multiplier:
                anomalies.append(tx)
                logger.warning(
                    f"價格異常: {tx.tx_hash[:10]}... "
                    f"{tx.amount} {token} (平均: {avg:.2f}, "
                    f"倍數: {tx.amount/avg:.2f}x)"
                )

        return anomalies

    def generate_quality_report(
        self,
        original_txs: List[WhaleTransaction],
        valid_txs: List[WhaleTransaction],
        invalid_txs: List[Tuple[WhaleTransaction, str]]
    ) -> dict:
        """
        生成資料品質報告

        Args:
            original_txs: 原始交易列表
            valid_txs: 有效交易列表
            invalid_txs: 無效交易列表 (含原因)

        Returns:
            品質報告字典
        """
        total_count = len(original_txs)
        valid_count = len(valid_txs)
        invalid_count = len(invalid_txs)

        # 統計無效原因
        invalid_reasons = {}
        for _, reason in invalid_txs:
            invalid_reasons[reason] = invalid_reasons.get(reason, 0) + 1

        report = {
            'total_transactions': total_count,
            'valid_transactions': valid_count,
            'invalid_transactions': invalid_count,
            'validity_rate': (valid_count / total_count * 100) if total_count > 0 else 0,
            'invalid_reasons': invalid_reasons,
            'timestamp': datetime.now().isoformat()
        }

        logger.info("=" * 60)
        logger.info("資料品質報告")
        logger.info("=" * 60)
        logger.info(f"總交易數: {total_count}")
        logger.info(f"有效交易: {valid_count} ({report['validity_rate']:.2f}%)")
        logger.info(f"無效交易: {invalid_count}")

        if invalid_reasons:
            logger.info("\n無效原因分布:")
            for reason, count in invalid_reasons.items():
                logger.info(f"  - {reason}: {count}")

        logger.info("=" * 60)

        return report


# ============================================================================
# 測試代碼
# ============================================================================
def test_validator():
    """測試驗證器"""
    from connectors.blockchain_base import TransactionDirection

    validator = BlockchainDataValidator()

    # 建立測試交易
    test_txs = [
        # 有效交易
        WhaleTransaction(
            blockchain='ETH',
            tx_hash='0x' + '1' * 64,
            timestamp=datetime.now(),
            from_address='0x' + '1' * 40,
            to_address='0x' + '2' * 40,
            amount=Decimal('100.5'),
            amount_usd=Decimal('300000'),
        ),
        # 無效交易 (地址格式錯誤)
        WhaleTransaction(
            blockchain='ETH',
            tx_hash='0x' + '2' * 64,
            timestamp=datetime.now(),
            from_address='invalid_address',
            to_address='0x' + '2' * 40,
            amount=Decimal('50'),
        ),
        # 無效交易 (金額為 0)
        WhaleTransaction(
            blockchain='ETH',
            tx_hash='0x' + '3' * 64,
            timestamp=datetime.now(),
            from_address='0x' + '1' * 40,
            to_address='0x' + '2' * 40,
            amount=Decimal('0'),
        ),
    ]

    # 測試驗證
    valid_txs, invalid_txs = validator.filter_valid_transactions(test_txs)

    # 生成報告
    report = validator.generate_quality_report(test_txs, valid_txs, invalid_txs)

    logger.info(f"\n報告: {report}")


if __name__ == '__main__':
    test_validator()
