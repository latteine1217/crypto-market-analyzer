import { Router } from 'express';
import * as blockchainService from '../services/blockchainService';

export const blockchainRoutes = Router();

blockchainRoutes.get('/whales/recent', async (req, res, next) => {
  try {
    const limit = req.query.limit ? parseInt(req.query.limit as string) : 50;
    const data = await blockchainService.getRecentWhaleTransactions(limit);
    res.json({ data });
  } catch (error) {
    next(error);
  }
});

blockchainRoutes.get('/:symbol/rich-list', async (req, res, next) => {
  try {
    const { symbol } = req.params;
    const days = req.query.days ? parseInt(req.query.days as string) : 30;
    const data = await blockchainService.getRichListStats(symbol.toUpperCase(), days);
    res.json({ data });
  } catch (error) {
    next(error);
  }
});
