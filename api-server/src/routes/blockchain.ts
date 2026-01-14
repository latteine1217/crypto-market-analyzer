import { Router } from 'express';
import * as blockchainService from '../services/blockchainService';

export const blockchainRoutes = Router();

blockchainRoutes.get('/:symbol/rich-list', async (req, res, next) => {
  try {
    const { symbol } = req.params;
    const days = req.query.days ? parseInt(req.query.days as string) : 30;
    const data = await blockchainService.getRichListStats(symbol.toUpperCase(), days);
    res.json(data);
  } catch (error) {
    next(error);
  }
});
