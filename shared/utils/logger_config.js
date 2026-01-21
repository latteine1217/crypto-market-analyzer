"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.setupLogger = setupLogger;
exports.getDefaultLogger = getDefaultLogger;
/**
 * 統一日誌配置模組 (Node.js)
 *
 * 提供標準化的 JSON 格式日誌配置
 * - 日誌輪轉：每日或達到 500MB
 * - 保留期限：30 天
 * - 格式：JSON
 */
const winston_1 = __importDefault(require("winston"));
const winston_daily_rotate_file_1 = __importDefault(require("winston-daily-rotate-file"));
const path_1 = __importDefault(require("path"));
const fs_1 = __importDefault(require("fs"));
/**
 * 設定統一日誌配置
 *
 * @param config - 日誌配置
 * @returns 配置好的 winston logger
 */
function setupLogger(config) {
    const { serviceName, logDir = 'logs', level = 'info', maxSize = '500m', maxFiles = '30d', jsonFormat = true, } = config;
    // 確保日誌目錄存在
    if (!fs_1.default.existsSync(logDir)) {
        fs_1.default.mkdirSync(logDir, { recursive: true });
    }
    // 自定義格式
    const customFormat = winston_1.default.format.combine(winston_1.default.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss.SSS' }), winston_1.default.format.errors({ stack: true }), winston_1.default.format.metadata(), jsonFormat
        ? winston_1.default.format.json()
        : winston_1.default.format.printf(({ timestamp, level, message, service, ...meta }) => {
            const metaStr = Object.keys(meta).length ? JSON.stringify(meta, null, 2) : '';
            return `${timestamp} [${level.toUpperCase()}] [${service}] ${message} ${metaStr}`;
        }));
    // 一般日誌輪轉配置
    const fileRotateTransport = new winston_daily_rotate_file_1.default({
        filename: path_1.default.join(logDir, `${serviceName}-%DATE%.log`),
        datePattern: 'YYYY-MM-DD',
        maxSize,
        maxFiles,
        level,
        format: customFormat,
        zippedArchive: true, // 壓縮舊日誌
    });
    // 錯誤日誌輪轉配置
    const errorRotateTransport = new winston_daily_rotate_file_1.default({
        filename: path_1.default.join(logDir, `${serviceName}.error-%DATE%.log`),
        datePattern: 'YYYY-MM-DD',
        maxSize,
        maxFiles,
        level: 'error',
        format: customFormat,
        zippedArchive: true,
    });
    // 控制台輸出
    const consoleTransport = new winston_1.default.transports.Console({
        level,
        format: winston_1.default.format.combine(winston_1.default.format.colorize(), winston_1.default.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss.SSS' }), winston_1.default.format.printf(({ timestamp, level, message, service }) => {
            return `${timestamp} ${level} [${service}] ${message}`;
        })),
    });
    // 建立 logger
    const logger = winston_1.default.createLogger({
        level,
        defaultMeta: { service: serviceName },
        transports: [consoleTransport, fileRotateTransport, errorRotateTransport],
        exceptionHandlers: [
            new winston_daily_rotate_file_1.default({
                filename: path_1.default.join(logDir, `${serviceName}.exceptions-%DATE%.log`),
                datePattern: 'YYYY-MM-DD',
                maxSize,
                maxFiles,
                zippedArchive: true,
            }),
        ],
        rejectionHandlers: [
            new winston_daily_rotate_file_1.default({
                filename: path_1.default.join(logDir, `${serviceName}.rejections-%DATE%.log`),
                datePattern: 'YYYY-MM-DD',
                maxSize,
                maxFiles,
                zippedArchive: true,
            }),
        ],
    });
    logger.info(`${serviceName} 日誌系統初始化完成`, {
        logDir: path_1.default.resolve(logDir),
        level,
        maxSize,
        maxFiles,
        jsonFormat,
    });
    return logger;
}
/**
 * 獲取預設配置的 logger
 *
 * @param serviceName - 服務名稱
 * @returns 配置好的 logger
 */
function getDefaultLogger(serviceName) {
    return setupLogger({
        serviceName,
        logDir: process.env.LOG_DIR || 'logs',
        level: process.env.LOG_LEVEL || 'info',
        maxSize: process.env.LOG_MAX_SIZE || '500m',
        maxFiles: process.env.LOG_MAX_FILES || '30d',
        jsonFormat: process.env.LOG_JSON !== 'false',
    });
}
