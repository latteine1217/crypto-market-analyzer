/**
 * 日誌工具
 * 使用共享的 ./shared/utils/logger_config
 */
import { getDefaultLogger } from '../shared/utils/logger_config';

export const logger = getDefaultLogger('data-collector');

// 便利方法 (保持與既有代碼相容)
export const log = {
  debug: (message: string, meta?: any) => logger.debug(message, meta),
  info: (message: string, meta?: any) => logger.info(message, meta),
  warn: (message: string, meta?: any) => logger.warn(message, meta),
  error: (message: string, error?: Error | any) => {
    if (error instanceof Error) {
      logger.error(message, { error: error.message, stack: error.stack });
    } else {
      logger.error(message, { error });
    }
  }
};