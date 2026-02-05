import { Router, Request, Response } from 'express';
import pool from '../database/pool';
import { CacheService } from '../database/cache';

const cacheService = new CacheService();

const router = Router();

const ETF_SYMBOL_MAP: Record<string, string> = {
  BTC: 'BTCUSDT',
  ETH: 'ETHUSDT',
};

const DEFAULT_ROLLING_WINDOW = 20;

const getWeekStart = (dateStr: string) => {
  const date = new Date(`${dateStr}T00:00:00Z`);
  const day = date.getUTCDay();
  const diff = (day + 6) % 7;
  date.setUTCDate(date.getUTCDate() - diff);
  return date.toISOString().split('T')[0];
};

const calculateRollingStats = (values: number[], window: number) => {
  const result: { avg: number | null; std: number | null; avgAbs: number | null }[] = [];
  for (let i = 0; i < values.length; i++) {
    const start = Math.max(0, i - window + 1);
    const slice = values.slice(start, i + 1).filter((v) => Number.isFinite(v));
    if (slice.length < 5) {
      result.push({ avg: null, std: null, avgAbs: null });
      continue;
    }
    const mean = slice.reduce((sum, v) => sum + v, 0) / slice.length;
    const meanAbs = slice.reduce((sum, v) => sum + Math.abs(v), 0) / slice.length;
    const variance = slice.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / slice.length;
    const std = Math.sqrt(variance);
    result.push({ avg: mean, std, avgAbs: meanAbs });
  }
  return result;
};

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
 * GET /api/etf-flows/analytics?asset=BTC&days=90
 * ETF Flow Trading Signals & Enriched Metrics
 */
router.get('/analytics', async (req: Request, res: Response) => {
  try {
    const assetType = (req.query.asset as string)?.toUpperCase() || 'BTC';
    const days = Math.min(parseInt(req.query.days as string) || 90, 365);

    const cacheKey = `etf_flows:analytics:${assetType}:${days}`;
    const cached = await cacheService.get(cacheKey);
    if (cached) {
      return res.json(cached);
    }

    const symbol = ETF_SYMBOL_MAP[assetType] || 'BTCUSDT';

    let marketId: number | undefined;
    const spotMarket = await pool.query(
      `SELECT m.id
       FROM markets m
       LEFT JOIN exchanges e ON m.exchange_id = e.id
       WHERE m.symbol = $1 AND m.market_type = 'spot'
       ORDER BY (e.name = 'bybit') DESC
       LIMIT 1`,
      [symbol]
    );
    if (spotMarket.rows[0]?.id) {
      marketId = spotMarket.rows[0].id;
    } else {
      const fallbackMarket = await pool.query(
        `SELECT m.id
         FROM markets m
         LEFT JOIN exchanges e ON m.exchange_id = e.id
         WHERE m.symbol = $1
         ORDER BY (e.name = 'bybit') DESC
         LIMIT 1`,
        [symbol]
      );
      marketId = fallbackMarket.rows[0]?.id;
    }

    const priceRows = marketId
      ? await pool.query(
          `SELECT time::date AS date, close::numeric AS close
           FROM ohlcv
           WHERE market_id = $1 AND timeframe = '1d'
             AND time >= CURRENT_DATE - INTERVAL '1 day' * $2
           ORDER BY date ASC`,
          [marketId, days]
        )
      : { rows: [] };

    const priceByDate = new Map<string, number>();
    for (const row of priceRows.rows) {
      priceByDate.set(row.date, parseFloat(row.close));
    }

    const productResult = await pool.query(
      `SELECT
          time::date as date,
          name as product_code,
          metadata->>'issuer' as issuer,
          value as net_flow_usd,
          (metadata->>'total_aum_usd')::numeric as total_aum_usd
        FROM global_indicators
        WHERE category = 'etf'
          AND metadata->>'asset_type' = $1
          AND time >= CURRENT_DATE - INTERVAL '1 day' * $2
        ORDER BY date ASC`,
      [assetType, days]
    );

    const byDate = new Map<
      string,
      {
        total_net_flow_usd: number;
        product_count: Set<string>;
        total_aum_usd: number;
        issuerTotals: Map<string, number>;
        productTotals: Map<string, number>;
      }
    >();

    const gbtcIbitDaily = new Map<string, { gbtc: number; ibit: number }>();

    for (const row of productResult.rows) {
      const date = row.date;
      const flow = parseFloat(row.net_flow_usd);
      const aum = row.total_aum_usd ? parseFloat(row.total_aum_usd) : 0;
      const issuer = row.issuer || 'Unknown';
      const product = row.product_code;

      const entry = byDate.get(date) || {
        total_net_flow_usd: 0,
        product_count: new Set<string>(),
        total_aum_usd: 0,
        issuerTotals: new Map<string, number>(),
        productTotals: new Map<string, number>(),
      };

      entry.total_net_flow_usd += flow;
      entry.product_count.add(product);
      if (aum > 0) entry.total_aum_usd += aum;
      entry.issuerTotals.set(issuer, (entry.issuerTotals.get(issuer) || 0) + flow);
      entry.productTotals.set(product, (entry.productTotals.get(product) || 0) + flow);
      byDate.set(date, entry);

      if (product === 'GBTC' || product === 'IBIT') {
        const current = gbtcIbitDaily.get(date) || { gbtc: 0, ibit: 0 };
        if (product === 'GBTC') current.gbtc += flow;
        if (product === 'IBIT') current.ibit += flow;
        gbtcIbitDaily.set(date, current);
      }
    }

    const dates = Array.from(byDate.keys()).sort((a, b) => new Date(a).getTime() - new Date(b).getTime());

    const totals = dates.map((date) => byDate.get(date)!.total_net_flow_usd);
    const rollingStats = calculateRollingStats(totals, DEFAULT_ROLLING_WINDOW);

    let cumulative = 0;
    const enrichedData = dates
      .map((date, idx) => {
        const entry = byDate.get(date)!;
        const totalNet = entry.total_net_flow_usd;
        cumulative += totalNet;

        const btcClose = priceByDate.get(date) || null;
        const netFlowBtc = btcClose ? totalNet / btcClose : null;

        const flowPctAum = entry.total_aum_usd > 0 ? totalNet / entry.total_aum_usd : null;

        const rolling = rollingStats[idx];
        const avgAbs = rolling.avgAbs;
        const flowPct20dAvg = avgAbs && avgAbs > 0 ? totalNet / avgAbs : null;
        const zscore =
          rolling.avg !== null && rolling.std && rolling.std > 0 ? (totalNet - rolling.avg) / rolling.std : null;

        const issuerTotals = Array.from(entry.issuerTotals.values()).map((v) => Math.abs(v));
        const totalAbsIssuer = issuerTotals.reduce((sum, v) => sum + v, 0);
        const sortedIssuer = issuerTotals.sort((a, b) => b - a);
        const top1 = sortedIssuer[0] || 0;
        const top3 = sortedIssuer.slice(0, 3).reduce((sum, v) => sum + v, 0);
        const top2 = sortedIssuer.slice(0, 2).reduce((sum, v) => sum + v, 0);

        const gbtcIbit = gbtcIbitDaily.get(date);
        const gbtcVsIbit = gbtcIbit ? gbtcIbit.gbtc - gbtcIbit.ibit : null;

        return {
          date,
          total_net_flow_usd: totalNet,
          cumulative_flow_usd: cumulative,
          product_count: entry.product_count.size,
          btc_close: btcClose,
          net_flow_btc: netFlowBtc,
          flow_pct_aum: flowPctAum,
          flow_pct_20d_avg: flowPct20dAvg,
          flow_zscore: zscore,
          flow_shock: zscore !== null && Math.abs(zscore) >= 2,
          issuer_concentration_top1: totalAbsIssuer > 0 ? top1 / totalAbsIssuer : null,
          issuer_concentration_top2: totalAbsIssuer > 0 ? top2 / totalAbsIssuer : null,
          issuer_concentration_top3: totalAbsIssuer > 0 ? top3 / totalAbsIssuer : null,
          gbtc_vs_ibit_divergence: gbtcVsIbit,
        };
      })
      .map((row, idx, arr) => {
        const prev = idx > 0 ? arr[idx - 1] : null;
        const priceChange = row.btc_close && prev?.btc_close ? row.btc_close - prev.btc_close : null;
        const divergence =
          priceChange !== null
            ? priceChange > 0 && row.total_net_flow_usd < 0
              ? 'price_up_outflow'
              : priceChange < 0 && row.total_net_flow_usd > 0
                ? 'price_down_inflow'
                : null
            : null;
        return {
          ...row,
          price_change: priceChange,
          price_divergence: divergence,
        };
      })
      .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());

    const latest = enrichedData[0];
    let inflowStreak = 0;
    let outflowStreak = 0;
    for (const row of enrichedData) {
      if (row.total_net_flow_usd > 0) {
        if (outflowStreak === 0) inflowStreak += 1;
        else break;
      } else if (row.total_net_flow_usd < 0) {
        if (inflowStreak === 0) outflowStreak += 1;
        else break;
      } else {
        break;
      }
    }

    const weeklyDivergenceMap = new Map<string, number>();
    for (const row of enrichedData) {
      if (row.gbtc_vs_ibit_divergence === null) continue;
      const weekStart = getWeekStart(row.date);
      weeklyDivergenceMap.set(
        weekStart,
        (weeklyDivergenceMap.get(weekStart) || 0) + (row.gbtc_vs_ibit_divergence || 0)
      );
    }
    const weekly_divergence = Array.from(weeklyDivergenceMap.entries())
      .map(([week_start, divergence_usd]) => ({ week_start, divergence_usd }))
      .sort((a, b) => new Date(a.week_start).getTime() - new Date(b.week_start).getTime());

    const lastUpdateResult = await pool.query(
      `SELECT MAX(time) AS latest_time
       FROM global_indicators
       WHERE category = 'etf' AND metadata->>'asset_type' = $1`,
      [assetType]
    );
    const lastUpdate = lastUpdateResult.rows[0]?.latest_time || null;

    const now = new Date();
    const stalenessHours = lastUpdate ? (now.getTime() - new Date(lastUpdate).getTime()) / 3600000 : null;
    const qualityStatus = stalenessHours !== null && stalenessHours <= 36 ? 'fresh' : 'stale';

    const response = {
      data: enrichedData,
      meta: {
        inflow_streak: inflowStreak,
        outflow_streak: outflowStreak,
        latest_flow: latest?.total_net_flow_usd || 0,
        last_update_time: lastUpdate,
        staleness_hours: stalenessHours,
        quality_status: qualityStatus,
        weekly_divergence,
      },
    };

    await cacheService.set(cacheKey, response, 600);
    res.json(response);
  } catch (error) {
    console.error('Error fetching ETF analytics:', error);
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

    // 快取 10 分鐘
    await cacheService.set(cacheKey, data, 600);

    res.json({ data });
  } catch (error) {
    console.error('Error fetching ETF products:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

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
