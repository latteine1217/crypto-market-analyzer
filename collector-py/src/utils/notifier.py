import requests
import redis
from loguru import logger
from config import settings

class TelegramNotifier:
    """
    Telegram 告警通知器
    """
    def __init__(self):
        self.enabled = bool(settings.tg_bot_token and settings.tg_chat_id)
        self.token = settings.tg_bot_token
        self.chat_id = settings.tg_chat_id
        
        # Redis 連接 (用於去重)
        try:
            self.redis = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=True
            )
        except Exception as e:
            logger.error(f"Failed to connect to Redis in TelegramNotifier: {e}")
            self.redis = None
        
        if not self.enabled:
            logger.warning("Telegram Notifier disabled: Missing token or chat_id")

    def send_message(self, text: str):
        if not self.enabled:
            return
            
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code != 200:
                logger.error(f"Failed to send TG message: {response.text}")
        except Exception as e:
            logger.error(f"Error sending TG notification: {e}")

    def send_signal_alert(self, signal: dict):
        """格式化訊號並發送告警 (含去重機制)"""
        if not self.enabled:
            return

        # 去重邏輯: 檢查是否已發送過此訊號 (根據 time + symbol + type)
        # 訊號 time 應該是 datetime 對象
        sig_time = signal['time'].timestamp() if hasattr(signal['time'], 'timestamp') else signal['time']
        dedup_key = f"alert_sent:{signal['symbol']}:{signal['signal_type']}:{sig_time}"
        
        if self.redis:
            try:
                if self.redis.exists(dedup_key):
                    # logger.debug(f"Skipping duplicate alert: {dedup_key}")
                    return
            except Exception as e:
                logger.warning(f"Redis dedup check failed: {e}")

        emoji = "🚀" if signal['side'] == 'bullish' else "📉" if signal['side'] == 'bearish' else "🔍"
        severity_emoji = "🔴" if signal['severity'] == 'critical' else "🟡" if signal['severity'] == 'warning' else "ℹ️"
        
        text = (
            f"{severity_emoji} *MARKET SIGNAL DETECTED*\n\n"
            f"*Type:* `{signal['signal_type']}`\n"
            f"*Symbol:* #{signal['symbol']}\n"
            f"*Side:* {emoji} {signal['side'].upper()}\n"
            f"*Price:* `{signal['price_at_signal'] if signal['price_at_signal'] else 'N/A'}`\n\n"
            f"> {signal['message']}\n\n"
            f"_Time: {signal['time'].strftime('%Y-%m-%d %H:%M:%S')} UTC_"
        )
        self.send_message(text)

        # 發送成功後寫入 Redis 去重記錄 (TTL 24小時)
        if self.redis:
            try:
                self.redis.setex(dedup_key, 86400, "1")
            except Exception as e:
                logger.warning(f"Failed to set Redis dedup key: {e}")
