import { Request, Response, NextFunction } from 'express';
import { logger } from '../utils/logger';
import { APIError, ErrorType } from '../shared/errors/ErrorClassifier';

export const errorHandler = (
  err: any,
  req: Request,
  res: Response,
  next: NextFunction
) => {
  const apiError = err instanceof APIError
    ? err
    : new APIError(
        err.statusCode || 500,
        ErrorType.UNKNOWN,
        'INTERNAL_ERROR',
        err.message || 'Internal Server Error',
        false,
        process.env.NODE_ENV === 'development' ? { stack: err.stack } : undefined
      );

  logger.error('API Error', {
    type: apiError.errorType,
    code: apiError.errorCode,
    message: apiError.message,
    path: req.path,
    method: req.method,
    details: apiError.details
  });

  res.status(apiError.statusCode).json(apiError.toJSON());
};
