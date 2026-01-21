"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.config = void 0;
const zod_1 = require("zod");
const dotenv_1 = __importDefault(require("dotenv"));
const path_1 = __importDefault(require("path"));
// Load environment variables from .env file if it exists
dotenv_1.default.config({ path: path_1.default.resolve(process.cwd(), '.env') });
const DatabaseSchema = zod_1.z.object({
    host: zod_1.z.string().default('localhost'),
    port: zod_1.z.coerce.number().default(5432),
    database: zod_1.z.string().default('crypto_db'),
    user: zod_1.z.string().default('crypto'),
    password: zod_1.z.string().default('crypto_pass'),
    max: zod_1.z.coerce.number().default(20),
    idleTimeoutMillis: zod_1.z.coerce.number().default(30000),
    connectionTimeoutMillis: zod_1.z.coerce.number().default(2000),
});
const RedisSchema = zod_1.z.object({
    host: zod_1.z.string().default('localhost'),
    port: zod_1.z.coerce.number().default(6379),
    db: zod_1.z.coerce.number().default(0),
    password: zod_1.z.string().optional(),
});
const ServerSchema = zod_1.z.object({
    port: zod_1.z.coerce.number().default(8080),
    env: zod_1.z.enum(['development', 'production', 'test']).default('development'),
    logLevel: zod_1.z.enum(['debug', 'info', 'warn', 'error']).default('info'),
    enableCache: zod_1.z.preprocess((v) => v !== 'false', zod_1.z.boolean()).default(true),
    cacheTtl: zod_1.z.coerce.number().default(5),
});
const CollectorSchema = zod_1.z.object({
    exchange: zod_1.z.string().default('binance'),
    flushBatchSize: zod_1.z.coerce.number().default(100),
    flushIntervalMs: zod_1.z.coerce.number().default(5000),
    maxBatchesPerFlush: zod_1.z.coerce.number().default(3),
    reconnectDelay: zod_1.z.coerce.number().default(5000),
    heartbeatInterval: zod_1.z.coerce.number().default(30000),
    maxReconnectAttempts: zod_1.z.coerce.number().default(10),
    symbols: zod_1.z.string().transform(s => s.split(',')).default('BTCUSDT,ETHUSDT'),
    streams: zod_1.z.string().transform(s => s.split(',')).default('trade,depth'),
});
const ConfigSchema = zod_1.z.object({
    server: ServerSchema,
    database: DatabaseSchema,
    redis: RedisSchema,
    collector: CollectorSchema,
});
// Helper to map environment variables to the schema
const getEnvConfig = () => ({
    server: {
        port: process.env.PORT,
        env: process.env.NODE_ENV,
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
        symbols: process.env.SYMBOLS,
        streams: process.env.STREAMS,
    },
});
exports.config = ConfigSchema.parse(getEnvConfig());
