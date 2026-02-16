import { Router } from 'express';
import * as blockchainService from '../services/blockchainService';
import { clampLimit } from '../shared/utils/limits';

export const blockchainRoutes = Router();

blockchainRoutes.get('/whales/recent', async (req, res, next) => {
  try {
    const limit = clampLimit(req.query.limit, { defaultValue: 50, max: 200 });
    const data = await blockchainService.getRecentWhaleTransactions(limit);
    res.json({ data });
  } catch (error) {
    next(error);
  }
});

blockchainRoutes.get('/:symbol/rich-list', async (req, res, next) => {
  try {
    const { symbol } = req.params;
    const days = clampLimit(req.query.days, { defaultValue: 30, max: 365 });
    const data = await blockchainService.getRichListStats(symbol.toUpperCase(), days);
    res.json({ data });
  } catch (error) {
    next(error);
  }
});
