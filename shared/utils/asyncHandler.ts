import { Request, Response, NextFunction } from 'express';

/**
 * 封裝 Express 路由處理器，自動捕捉錯誤並傳遞給 next()
 */
export const asyncHandler = (fn: Function) => (req: Request, res: Response, next: NextFunction) => {
  return Promise.resolve(fn(req, res, next)).catch(next);
};
