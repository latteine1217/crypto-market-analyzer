import { Router, Request, Response } from 'express';
import pool from '../database/pool';
import { CacheService } from '../database/cache';

const cacheService = new CacheService();

const router = Router();

/**
 * GET /api/fred/indicators
 * 取得 FRED 經濟指標數據
 * Query Params:
 *   - series: 逗號分隔的指標代碼 (例如: UNRATE,CPIAUCSL,FEDFUNDS,GDP)
 *   - days: 查詢天數 (預設 180，最大 1825 = 5年)
 */
router.get('/indicators', async (req: Request, res: Response) => {
  try {
    const seriesParam = req.query.series as string || 'UNRATE,CPIAUCSL,FEDFUNDS,GDP';
    const seriesList = seriesParam.split(',').map(s => s.trim());
    const days = Math.min(parseInt(req.query.days as string) || 180, 1825);
    
    const cacheKey = `fred:indicators:${seriesParam}:${days}`;
    const cached = await cacheService.get(cacheKey);
    
    if (cached) {
      return res.json(cached);
    }

    // 查詢指定的經濟指標
    const result = await pool.query(
      `SELECT 
         name as series_id,
         time as timestamp,
         value,
         (metadata->>'forecast_value')::numeric as forecast_value
       FROM global_indicators
       WHERE category = 'macro'
         AND name = ANY($1)
         AND time >= NOW() - INTERVAL '1 day' * $2
       ORDER BY name, time ASC`,
      [seriesList, days]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ 
        error: 'No FRED data available for the requested series',
        requested_series: seriesList
      });
    }

    // 組織資料結構：按 series_id 分組
    const dataBySection = result.rows.reduce((acc: any, row: any) => {
      if (!acc[row.series_id]) {
        acc[row.series_id] = [];
      }
      acc[row.series_id].push({
        timestamp: row.timestamp,
        value: parseFloat(row.value),
        forecast: row.forecast_value ? parseFloat(row.forecast_value) : null
      });
      return acc;
    }, {});

    // 計算每個指標的最新值與變化
    const summary = seriesList.map(seriesId => {
      const data = dataBySection[seriesId] || [];
      if (data.length === 0) {
        return {
          series_id: seriesId,
          latest_value: null,
          previous_value: null,
          change: null,
          change_percent: null,
          timestamp: null
        };
      }

      const latest = data[data.length - 1];
      const previous = data.length > 1 ? data[data.length - 2] : null;
      
      let change: number | null = null;
      let changePercent: string | null = null;
      
      if (previous) {
        change = latest.value - previous.value;
        changePercent = ((change / previous.value) * 100).toFixed(2);
      }

      return {
        series_id: seriesId,
        latest_value: latest.value,
        previous_value: previous?.value || null,
        change: change,
        change_percent: changePercent,
        timestamp: latest.timestamp,
        name: getSeriesName(seriesId),
        unit: getSeriesUnit(seriesId)
      };
    });

    const response = {
      summary,
      data: dataBySection,
      metadata: {
        days_requested: days,
        series_count: seriesList.length,
        total_records: result.rows.length
      }
    };

    // 快取 15 分鐘（FRED 資料更新頻率低）
    await cacheService.set(cacheKey, response, 900);

    res.json({ data: response });
  } catch (error) {
    console.error('Error fetching FRED indicators:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

/**
 * GET /api/fred/latest
 * 取得所有 FRED 指標的最新數值
 */
router.get('/latest', async (req: Request, res: Response) => {
  try {
    const cacheKey = 'fred:latest';
    const cached = await cacheService.get(cacheKey);
    
    if (cached) {
      return res.json({ data: cached });
    }

    const result = await pool.query(
      `SELECT DISTINCT ON (name)
         name as series_id,
         time as timestamp,
         value,
         (metadata->>'forecast_value')::numeric as forecast_value
       FROM global_indicators
       WHERE category = 'macro'
       ORDER BY name, time DESC`
    );

    const data = result.rows.map(row => ({
      series_id: row.series_id,
      name: getSeriesName(row.series_id),
      value: parseFloat(row.value),
      forecast: row.forecast_value ? parseFloat(row.forecast_value) : null,
      timestamp: row.timestamp,
      unit: getSeriesUnit(row.series_id),
      description: getSeriesDescription(row.series_id)
    }));

    // 快取 10 分鐘
    await cacheService.set(cacheKey, data, 600);

    res.json({ data });
  } catch (error) {
    console.error('Error fetching latest FRED data:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

/**
 * 取得指標名稱
 */
function getSeriesName(seriesId: string): string {
  const names: Record<string, string> = {
    'UNRATE': 'Unemployment Rate',
    'CPIAUCSL': 'Consumer Price Index',
    'FEDFUNDS': 'Federal Funds Rate',
    'GDP': 'Gross Domestic Product',
    'DGS10': '10-Year Treasury Rate',
    'DEXUSEU': 'USD/EUR Exchange Rate',
    'DCOILWTICO': 'Crude Oil Price (WTI)'
  };
  return names[seriesId] || seriesId;
}

/**
 * 取得指標單位
 */
function getSeriesUnit(seriesId: string): string {
  const units: Record<string, string> = {
    'UNRATE': '%',
    'CPIAUCSL': 'Index',
    'FEDFUNDS': '%',
    'GDP': 'Billion USD',
    'DGS10': '%',
    'DEXUSEU': 'EUR/USD',
    'DCOILWTICO': 'USD/Barrel'
  };
  return units[seriesId] || '';
}

/**
 * 取得指標描述
 */
function getSeriesDescription(seriesId: string): string {
  const descriptions: Record<string, string> = {
    'UNRATE': 'Percentage of labor force that is unemployed',
    'CPIAUCSL': 'Measure of average change in prices over time',
    'FEDFUNDS': 'Interest rate at which banks lend to each other overnight',
    'GDP': 'Total value of goods and services produced',
    'DGS10': 'Yield on 10-year U.S. Treasury bonds',
    'DEXUSEU': 'Exchange rate between U.S. Dollar and Euro',
    'DCOILWTICO': 'Price per barrel of West Texas Intermediate crude oil'
  };
  return descriptions[seriesId] || 'Economic indicator from FRED database';
}

export default router;
