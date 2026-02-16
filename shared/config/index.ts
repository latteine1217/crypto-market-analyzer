import { z } from 'zod';
import dotenv from 'dotenv';
import path from 'path';

// Load environment variables from .env file if it exists
dotenv.config({ path: path.resolve(process.cwd(), '.env') });

const DatabaseSchema = z.object({
  host: z.string().default('localhost'),
  port: z.coerce.number().default(5432),
  database: z.string().default('crypto_db'),
  user: z.string().default('crypto'),
  password: z.string().default('crypto_pass'),
  max: z.coerce.number().default(20),
  idleTimeoutMillis: z.coerce.number().default(30000),
  connectionTimeoutMillis: z.coerce.number().default(2000),
});

const RedisSchema = z.object({
  host: z.string().default('localhost'),
  port: z.coerce.number().default(6379),
  db: z.coerce.number().default(0),
  password: z.string().optional(),
});

const ServerSchema = z.object({
  port: z.coerce.number().default(8080),
  env: z.enum(['development', 'production', 'test']).default('development'),
  logLevel: z.enum(['debug', 'info', 'warn', 'error']).default('info'),
  enableCache: z.preprocess((v) => v !== 'false', z.boolean()).default(true),
  cacheTtl: z.coerce.number().default(5),
});

const CollectorSchema = z.object({
  exchange: z.string().default('bybit'),
  flushBatchSize: z.coerce.number().default(100),
  flushIntervalMs: z.coerce.number().default(5000),
  maxBatchesPerFlush: z.coerce.number().default(3),
  reconnectDelay: z.coerce.number().default(5000),
  heartbeatInterval: z.coerce.number().default(30000),
  maxReconnectAttempts: z.coerce.number().default(10),
  symbols: z.string().default('BTCUSDT,ETHUSDT').transform(s => s.split(',')),
  streams: z.string().default('trade,depth').transform(s => s.split(',')),
});

const ConfigSchema = z.object({
  server: ServerSchema,
  database: DatabaseSchema,
  redis: RedisSchema,
  collector: CollectorSchema,
});

export type Config = z.infer<typeof ConfigSchema>;

// Helper to map environment variables to the schema
const getEnvConfig = () => ({
  server: {
    port: process.env.PORT,
    env: process.env.NODE_ENV || process.env.ENVIRONMENT,
    logLevel: process.env.LOG_LEVEL,
    enableCache: process.env.ENABLE_CACHE,
    cacheTtl: process.env.CACHE_TTL,
  },
  database: {
    host: process.env.POSTGRES_HOST,
    port: process.env.POSTGRES_PORT,
    database: process.env.POSTGRES_DB,
    user: process.env.POSTGRES_USER,
    password: process.env.POSTGRES_PASSWORD,
  },
  redis: {
    host: process.env.REDIS_HOST,
    port: process.env.REDIS_PORT,
    db: process.env.REDIS_DB,
    password: process.env.REDIS_PASSWORD,
  },
  collector: {
    exchange: process.env.EXCHANGE,
    flushBatchSize: process.env.FLUSH_BATCH_SIZE,
    flushIntervalMs: process.env.FLUSH_INTERVAL_MS,
    maxBatchesPerFlush: process.env.FLUSH_MAX_BATCHES,
    reconnectDelay: process.env.WS_RECONNECT_DELAY,
    heartbeatInterval: process.env.WS_HEARTBEAT_INTERVAL,
    maxReconnectAttempts: process.env.WS_MAX_RECONNECT_ATTEMPTS,
    symbols: process.env.SYMBOLS || process.env.WS_SYMBOLS,
    streams: process.env.STREAMS || process.env.WS_STREAMS,
  },
});

export const config = ConfigSchema.parse(getEnvConfig());
