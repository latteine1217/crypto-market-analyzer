/**
 * 統一錯誤分類器
 * 定義標準錯誤類型與 API 錯誤類別
 */

export enum ErrorType {
  NETWORK = 'network',
  RATE_LIMIT = 'rate_limit',
  DATABASE = 'database',
  VALIDATION = 'validation',
  NOT_FOUND = 'not_found',
  UNAUTHORIZED = 'unauthorized',
  INTERNAL = 'internal',
  UNKNOWN = 'unknown'
}

export class APIError extends Error {
  constructor(
    public statusCode: number,
    public errorType: ErrorType,
    public errorCode: string,
    message: string,
    public isRetryable: boolean = false,
    public details?: any
  ) {
    super(message);
    this.name = 'APIError';
    Object.setPrototypeOf(this, APIError.prototype);
  }

  toJSON() {
    return {
      success: false,
      error: {
        type: this.errorType,
        code: this.errorCode,
        message: this.message,
        details: this.details
      }
    };
  }
}

// 常用錯誤定義
export const Errors = {
  NotFound: (resource: string = 'Resource') => 
    new APIError(404, ErrorType.NOT_FOUND, 'NOT_FOUND', `${resource} not found`),
  
  BadRequest: (message: string, details?: any) => 
    new APIError(400, ErrorType.VALIDATION, 'BAD_REQUEST', message, false, details),
  
  Unauthorized: (message: string = 'Unauthorized access') => 
    new APIError(401, ErrorType.UNAUTHORIZED, 'UNAUTHORIZED', message),
  
  RateLimit: (message: string = 'Too many requests') => 
    new APIError(429, ErrorType.RATE_LIMIT, 'RATE_LIMIT_EXCEEDED', message, true),
  
  DatabaseError: (message: string = 'Database operation failed', isRetryable: boolean = false) => 
    new APIError(500, ErrorType.DATABASE, 'DATABASE_ERROR', message, isRetryable),
  
  Internal: (message: string = 'Internal server error') => 
    new APIError(500, ErrorType.INTERNAL, 'INTERNAL_SERVER_ERROR', message),
};
