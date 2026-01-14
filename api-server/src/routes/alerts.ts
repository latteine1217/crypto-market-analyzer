import { Router } from 'express';
import * as alertService from '../services/alertService';

export const alertRoutes = Router();

// GET /api/alerts - 獲取所有警報
alertRoutes.get('/', async (req, res, next) => {
  try {
    const alerts = await alertService.getAllAlerts();
    res.json({ data: alerts });
  } catch (error) {
    next(error);
  }
});

// POST /api/alerts - 創建警報
alertRoutes.post('/', async (req, res, next) => {
  try {
    const { symbol, condition, target_price } = req.body;
    
    if (!symbol || !condition || !target_price) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    if (!['above', 'below'].includes(condition)) {
      return res.status(400).json({ error: 'Invalid condition' });
    }

    const alert = await alertService.createAlert(symbol, condition, Number(target_price));
    res.json({ data: alert });
  } catch (error) {
    next(error);
  }
});

// DELETE /api/alerts/:id - 刪除警報
alertRoutes.delete('/:id', async (req, res, next) => {
  try {
    const id = parseInt(req.params.id);
    await alertService.deleteAlert(id);
    res.json({ success: true });
  } catch (error) {
    next(error);
  }
});
