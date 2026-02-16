import { APIError, ErrorType } from '../errors/ErrorClassifier';

type ResponseLike = {
  status: (code: number) => { json: (body: any) => any };
};

export const sendError = (
  res: ResponseLike,
  err: any,
  fallbackMessage: string,
  options?: {
    statusCode?: number;
    errorType?: ErrorType;
    errorCode?: string;
    details?: any;
  }
) => {
  const statusCode = options?.statusCode || err?.statusCode || 500;
  const errorType = options?.errorType || ErrorType.INTERNAL;
  const errorCode = options?.errorCode || 'INTERNAL_SERVER_ERROR';
  const message = err?.message || fallbackMessage;

  const apiError = err instanceof APIError
    ? err
    : new APIError(statusCode, errorType, errorCode, message, false, options?.details);

  const payload = apiError.toJSON();
  return res.status(apiError.statusCode).json({
    success: payload.success,
    error: apiError.message,
    error_detail: payload.error
  });
};
