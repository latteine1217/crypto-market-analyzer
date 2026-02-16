import { Router } from 'express';
import * as alertService from '../services/alertService';
import { sendError } from '../shared/utils/sendError';
import { ErrorType } from '../shared/errors/ErrorClassifier';
import { clampLimit } from '../shared/utils/limits';

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

// GET /api/alerts/signals - 獲取系統生成的市場訊號
alertRoutes.get('/signals', async (req, res, next) => {
  try {
    const limit = clampLimit(req.query.limit, { defaultValue: 50, max: 200 });
    const signals = await alertService.getMarketSignals(limit);
    res.json({ data: signals });
  } catch (error) {
    next(error);
  }
});

// POST /api/alerts - 創建警報
alertRoutes.post('/', async (req, res, next) => {
  try {
    const { symbol, condition, target_price } = req.body;
    
    if (!symbol || !condition || !target_price) {
      return sendError(res, null, 'Missing required fields', {
        statusCode: 400,
        errorType: ErrorType.VALIDATION,
        errorCode: 'BAD_REQUEST'
      });
    }

    if (!['above', 'below'].includes(condition)) {
      return sendError(res, null, 'Invalid condition', {
        statusCode: 400,
        errorType: ErrorType.VALIDATION,
        errorCode: 'BAD_REQUEST'
      });
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
