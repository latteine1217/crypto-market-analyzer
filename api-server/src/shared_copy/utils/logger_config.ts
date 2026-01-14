/**
 * 統一日誌配置模組 (Node.js)
 *
 * 提供標準化的 JSON 格式日誌配置
 * - 日誌輪轉：每日或達到 500MB
 * - 保留期限：30 天
 * - 格式：JSON
 */
import winston from 'winston';
import DailyRotateFile from 'winston-daily-rotate-file';
import path from 'path';
import fs from 'fs';

export interface LoggerConfig {
  serviceName: string;
  logDir?: string;
  level?: string;
  maxSize?: string;
  maxFiles?: string;
  jsonFormat?: boolean;
}

/**
 * 設定統一日誌配置
 *
 * @param config - 日誌配置
 * @returns 配置好的 winston logger
 */
export function setupLogger(config: LoggerConfig): winston.Logger {
  const {
    serviceName,
    logDir = 'logs',
    level = 'info',
    maxSize = '500m',
    maxFiles = '30d',
    jsonFormat = true,
  } = config;

  // 確保日誌目錄存在
  if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir, { recursive: true });
  }

  // 自定義格式
  const customFormat = winston.format.combine(
    winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss.SSS' }),
    winston.format.errors({ stack: true }),
    winston.format.metadata(),
    jsonFormat
      ? winston.format.json()
      : winston.format.printf(({ timestamp, level, message, service, ...meta }) => {
          const metaStr = Object.keys(meta).length ? JSON.stringify(meta, null, 2) : '';
          return `${timestamp} [${level.toUpperCase()}] [${service}] ${message} ${metaStr}`;
        })
  );

  // 一般日誌輪轉配置
  const fileRotateTransport = new DailyRotateFile({
    filename: path.join(logDir, `${serviceName}-%DATE%.log`),
    datePattern: 'YYYY-MM-DD',
    maxSize,
    maxFiles,
    level,
    format: customFormat,
    zippedArchive: true, // 壓縮舊日誌
  });

  // 錯誤日誌輪轉配置
  const errorRotateTransport = new DailyRotateFile({
    filename: path.join(logDir, `${serviceName}.error-%DATE%.log`),
    datePattern: 'YYYY-MM-DD',
    maxSize,
    maxFiles,
    level: 'error',
    format: customFormat,
    zippedArchive: true,
  });

  // 控制台輸出
  const consoleTransport = new winston.transports.Console({
    level,
    format: winston.format.combine(
      winston.format.colorize(),
      winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss.SSS' }),
      winston.format.printf(({ timestamp, level, message, service }) => {
        return `${timestamp} ${level} [${service}] ${message}`;
      })
    ),
  });

  // 建立 logger
  const logger = winston.createLogger({
    level,
    defaultMeta: { service: serviceName },
    transports: [consoleTransport, fileRotateTransport, errorRotateTransport],
    exceptionHandlers: [
      new DailyRotateFile({
        filename: path.join(logDir, `${serviceName}.exceptions-%DATE%.log`),
        datePattern: 'YYYY-MM-DD',
        maxSize,
        maxFiles,
        zippedArchive: true,
      }),
    ],
    rejectionHandlers: [
      new DailyRotateFile({
        filename: path.join(logDir, `${serviceName}.rejections-%DATE%.log`),
        datePattern: 'YYYY-MM-DD',
        maxSize,
        maxFiles,
        zippedArchive: true,
      }),
    ],
  });

  logger.info(`${serviceName} 日誌系統初始化完成`, {
    logDir: path.resolve(logDir),
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
export function getDefaultLogger(serviceName: string): winston.Logger {
  return setupLogger({
    serviceName,
    logDir: process.env.LOG_DIR || 'logs',
    level: process.env.LOG_LEVEL || 'info',
    maxSize: process.env.LOG_MAX_SIZE || '500m',
    maxFiles: process.env.LOG_MAX_FILES || '30d',
    jsonFormat: process.env.LOG_JSON !== 'false',
  });
}
