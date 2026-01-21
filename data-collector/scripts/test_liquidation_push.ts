import Redis from 'ioredis';
import { MessageType } from '../src/types';

// 模擬 RedisKeys 邏輯
const REDIS_PREFIX = 'crypto:v2';
const getQueueKey = (type: string, exchange: string = '') => {
  const exchangePart = exchange ? `${exchange.toLowerCase()}:` : '';
  return `${REDIS_PREFIX}:queue:${exchangePart}${type}`;
};

const redis = new Redis({
  host: process.env.REDIS_HOST || 'localhost',
  port: parseInt(process.env.REDIS_PORT || '6379'),
});

async function testLiquidationFlush() {
  const mockLiquidation = {
    type: MessageType.LIQUIDATION,
    exchange: 'bybit',
    data: {
      symbol: 'BTCUSDT',
      side: 'buy',
      price: 42000.5,
      quantity: 0.1,
      timestamp: Date.now()
    },
    receivedAt: Date.now()
  };

  const queueKey = getQueueKey(MessageType.LIQUIDATION, 'bybit');
  console.log(`Pushing to key: ${queueKey}`);
  
  await redis.rpush(queueKey, JSON.stringify(mockLiquidation));
  console.log('✅ Mock liquidation pushed to Redis queue');
  
  // 等待 10 秒讓 DBFlusher 處理
  console.log('Waiting 10 seconds for DBFlusher...');
  setTimeout(async () => {
    process.exit(0);
  }, 10000);
}

testLiquidationFlush().catch(console.error);