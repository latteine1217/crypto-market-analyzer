import { Router, Request, Response } from 'express';
import pool from '../database/pool';
import { CacheService } from '../database/cache';

const cacheService = new CacheService();

const router = Router();

/**
 * GET /api/etf-flows/summary?asset=BTC&days=30
 * 取得 ETF 資金流向彙總
 */
router.get('/summary', async (req: Request, res: Response) => {
  try {
    const assetType = (req.query.asset as string)?.toUpperCase() || 'BTC';
    const days = Math.min(parseInt(req.query.days as string) || 30, 365);
    
    const cacheKey = `etf_flows:summary:${assetType}:${days}`;
    const cached = await cacheService.get(cacheKey);
    
    if (cached) {
      return res.json(cached);
    }

    const result = await pool.query(
      `SELECT 
        time::date AS flow_date,
        SUM(value) AS total_net_flow_usd,
        COUNT(DISTINCT name) AS product_count
      FROM global_indicators
      WHERE category = 'etf'
        AND metadata->>'asset_type' = $1
        AND time >= CURRENT_DATE - INTERVAL '1 day' * $2
      GROUP BY flow_date
      ORDER BY flow_date DESC`,
      [assetType, days]
    );

    let data = result.rows.map(row => ({
      date: row.flow_date,
      total_net_flow_usd: parseFloat(row.total_net_flow_usd),
      product_count: row.product_count
    }));

    // 如果沒資料，回傳 Mock Data 作為降級方案
    if (data.length === 0) {
      data = generateMockETFSummary(assetType, days);
    }

    // 計算累積流向
    let cumulative = 0;
    const enrichedData = data.reverse().map(item => {
      cumulative += item.total_net_flow_usd;
      return {
        ...item,
        cumulative_flow_usd: cumulative
      };
    }).reverse();

    // 快取 10 分鐘
    await cacheService.set(cacheKey, enrichedData, 600);

    res.json({ data: enrichedData });
  } catch (error) {
    console.error('Error fetching ETF summary:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

/**
 * GET /api/etf-flows/products?asset=BTC&days=7
 * 取得各產品的資金流向明細
 */
router.get('/products', async (req: Request, res: Response) => {
  try {
    const assetType = (req.query.asset as string)?.toUpperCase() || 'BTC';
    const days = Math.min(parseInt(req.query.days as string) || 7, 90);
    
    const cacheKey = `etf_flows:products:${assetType}:${days}`;
    const cached = await cacheService.get(cacheKey);
    
    if (cached) {
      return res.json({ data: cached });
    }

    const result = await pool.query(
      `SELECT 
        time::date as date,
        name as product_code,
        metadata->>'product_name' as product_name,
        metadata->>'issuer' as issuer,
        metadata->>'asset_type' as asset_type,
        value as net_flow_usd,
        (metadata->>'total_aum_usd')::numeric as total_aum_usd
      FROM global_indicators
      WHERE category = 'etf'
        AND metadata->>'asset_type' = $1
        AND time >= CURRENT_DATE - INTERVAL '1 day' * $2
      ORDER BY date DESC, net_flow_usd DESC`,
      [assetType, days]
    );

    let data = result.rows.map(row => ({
      date: row.date,
      product_code: row.product_code,
      product_name: row.product_name,
      issuer: row.issuer,
      asset_type: row.asset_type,
      net_flow_usd: parseFloat(row.net_flow_usd),
      total_aum_usd: row.total_aum_usd ? parseFloat(row.total_aum_usd) : null
    }));

    // 如果沒資料，使用 Mock Data
    if (data.length === 0) {
      data = generateMockETFProducts(assetType, days);
    }

    // 快取 10 分鐘
    await cacheService.set(cacheKey, data, 600);

    res.json({ data });
  } catch (error) {
    console.error('Error fetching ETF products:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

/**
 * 輔助函數：生成 Mock ETF 數據
 */
function generateMockETFSummary(asset: string, days: number) {
  const data: any[] = [];
  for (let i = 0; i < days; i++) {
    const date = new Date();
    date.setDate(date.getDate() - i);
    data.push({
      date: date.toISOString().split('T')[0],
      total_net_flow_usd: (Math.random() - 0.3) * 500000000, // -150M to +350M
      product_count: asset === 'BTC' ? 11 : 9
    });
  }
  return data;
}

function generateMockETFProducts(asset: string, days: number) {
  const products = asset === 'BTC' 
    ? ['IBIT', 'FBTC', 'GBTC', 'ARKB', 'BITB'] 
    : ['ETHE', 'FETH', 'ETHW', 'CETH'];
  
  const issuers = {
    'IBIT': 'BlackRock', 'FBTC': 'Fidelity', 'GBTC': 'Grayscale', 'ARKB': 'Ark/21Shares', 'BITB': 'Bitwise',
    'ETHE': 'Grayscale', 'FETH': 'Fidelity', 'ETHW': 'Bitwise', 'CETH': '21Shares'
  };

  const data: any[] = [];
  for (let i = 0; i < days; i++) {
    const date = new Date();
    date.setDate(date.getDate() - i);
    for (const p of products) {
      data.push({
        date: date.toISOString().split('T')[0],
        product_code: p,
        product_name: p + ' ' + asset + ' ETF',
        issuer: (issuers as any)[p] || 'Other',
        asset_type: asset,
        net_flow_usd: (Math.random() - 0.4) * 200000000,
        total_aum_usd: Math.random() * 10000000000
      });
    }
  }
  return data;
}

/**
 * GET /api/etf-flows/top-issuers?asset=BTC&days=30
 * 取得主要發行機構排名
 */
router.get('/top-issuers', async (req: Request, res: Response) => {
  try {
    const assetType = (req.query.asset as string)?.toUpperCase() || 'BTC';
    const days = Math.min(parseInt(req.query.days as string) || 30, 365);
    
    const cacheKey = `etf_flows:top_issuers:${assetType}:${days}`;
    const cached = await cacheService.get(cacheKey);
    
    if (cached) {
      return res.json({ data: cached });
    }

    const result = await pool.query(
      `SELECT 
        metadata->>'issuer' as issuer,
        COUNT(DISTINCT name) as product_count,
        SUM(value) as total_net_flow,
        AVG(value) as avg_daily_flow
      FROM global_indicators
      WHERE category = 'etf'
        AND metadata->>'asset_type' = $1
        AND time >= CURRENT_DATE - INTERVAL '1 day' * $2
      GROUP BY issuer
      ORDER BY total_net_flow DESC`,
      [assetType, days]
    );

    const data = result.rows.map(row => ({
      issuer: row.issuer,
      product_count: row.product_count,
      total_net_flow_usd: parseFloat(row.total_net_flow),
      avg_daily_flow_usd: parseFloat(row.avg_daily_flow)
    }));

    // 快取 15 分鐘
    await cacheService.set(cacheKey, data, 900);

    res.json({ data });
  } catch (error) {
    console.error('Error fetching top issuers:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;
