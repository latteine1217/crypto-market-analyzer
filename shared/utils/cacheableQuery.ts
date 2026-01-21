import { Request, Response } from 'express';
import { asyncHandler } from './asyncHandler';

export interface ICacheService {
  get<T>(key: string): Promise<T | null>;
  set(key: string, value: any, ttl?: number): Promise<void>;
  makeKey(...parts: (string | number)[]): string;
}

/**
 * 建立可快取的查詢處理器
 */
export const createCacheableQuery = (getCacheService: () => ICacheService) => (
  cacheKeyFactory: (params: any, query: any) => string,
  queryFn: (params: any, query: any) => Promise<any>,
  options: { ttl?: number, sourceName?: string } = {}
) => asyncHandler(async (req: Request, res: Response) => {
  const cache = getCacheService();
  const cacheKey = cacheKeyFactory(req.params, req.query);
  
  const cached = await cache.get(cacheKey);
  if (cached) {
    return res.json({ 
      data: cached, 
      cached: true,
      source: options.sourceName || 'cache' 
    });
  }

  const data = await queryFn(req.params, req.query);
  await cache.set(cacheKey, data, options.ttl);

  res.json({ 
    data, 
    cached: false,
    source: options.sourceName || 'db'
  });
});