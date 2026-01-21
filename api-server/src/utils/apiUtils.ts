import { createCacheableQuery } from '../shared/utils/cacheableQuery';
import { CacheService } from '../database/cache';

export const cacheableQuery = createCacheableQuery(() => new CacheService());
