import sys
import os
from datetime import datetime, timezone

# 將 src 加入 PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.notifier import TelegramNotifier
from loguru import logger

def test_alert():
    notifier = TelegramNotifier()
    
    if not notifier.enabled:
        logger.error("Telegram Notifier is NOT enabled. Check your .env file and settings.")
        return

    logger.info("Sending test signal alert...")
    
    test_signal = {
        'time': datetime.now(timezone.utc),
        'symbol': 'BTCUSDT',
        'signal_type': 'test_alert',
        'side': 'bullish',
        'severity': 'info',
        'price_at_signal': 69420.5,
        'message': "This is a test alert to verify Telegram integration. De-duplication is active."
    }
    
    # 測試發送格式化告警
    notifier.send_signal_alert(test_signal)
    logger.success("Test alert sent! Please check your Telegram.")

if __name__ == "__main__":
    test_alert()
