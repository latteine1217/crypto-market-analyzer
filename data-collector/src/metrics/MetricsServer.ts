/**
 * Prometheus Metrics Server
 * 提供系統運行指標給 Prometheus 收集
 */
import * as promClient from 'prom-client';
import * as http from 'http';
import { log } from '../utils/logger';

export class MetricsServer {
  private server: http.Server | null = null;
  private register: typeof promClient.register;
  private port: number;

  // ========== WebSocket 指標 ==========
  public wsMessagesTotal: promClient.Counter<string>;
  public wsConnectionStatus: promClient.Gauge<string>;
  public wsReconnectsTotal: promClient.Counter<string>;
  public wsErrorsTotal: promClient.Counter<string>;
  public wsMessageProcessingDuration: promClient.Histogram<string>;

  // ========== 交易數據指標 ==========
  public tradesCollectedTotal: promClient.Counter<string>;
  public tradesQueueSize: promClient.Gauge<string>;

  // ========== 訂單簿指標 ==========
  public orderbookUpdatesTotal: promClient.Counter<string>;
  public orderbookSnapshotsTotal: promClient.Counter<string>;
  public orderbookQueueSize: promClient.Gauge<string>;
  public orderbookBestBidPrice: promClient.Gauge<string>;
  public orderbookBestAskPrice: promClient.Gauge<string>;
  public orderbookSpread: promClient.Gauge<string>;
  public orderbookSpreadBps: promClient.Gauge<string>;

  // ========== Redis 指標 ==========
  public redisQueuePushTotal: promClient.Counter<string>;
  public redisQueueErrors: promClient.Counter<string>;
  public redisQueueSize: promClient.Gauge<string>;

  // ========== 資料庫指標 ==========
  public dbFlushedTotal: promClient.Counter<string>;
  public dbFlushErrors: promClient.Counter<string>;
  public dbFlushDuration: promClient.Histogram<string>;
  public dbIsFlushing: promClient.Gauge<string>;

  // ========== 系統指標 ==========
  public collectorUptime: promClient.Gauge<string>;
  public collectorRunning: promClient.Gauge<string>;

  constructor(port: number = 8001) {
    this.port = port;
    this.register = new promClient.Registry();

    // 啟用預設指標（CPU、Memory 等）
    promClient.collectDefaultMetrics({ register: this.register });

    // ========== 初始化自定義指標 ==========

    // WebSocket 指標
    this.wsMessagesTotal = new promClient.Counter({
      name: 'ws_collector_messages_total',
      help: 'Total number of WebSocket messages received',
      labelNames: ['exchange', 'type'],
      registers: [this.register]
    });

    this.wsConnectionStatus = new promClient.Gauge({
      name: 'ws_collector_connection_status',
      help: 'WebSocket connection status (1=connected, 0=disconnected)',
      labelNames: ['exchange'],
      registers: [this.register]
    });

    this.wsReconnectsTotal = new promClient.Counter({
      name: 'ws_collector_reconnects_total',
      help: 'Total number of WebSocket reconnections',
      labelNames: ['exchange'],
      registers: [this.register]
    });

    this.wsErrorsTotal = new promClient.Counter({
      name: 'ws_collector_errors_total',
      help: 'Total number of WebSocket errors',
      labelNames: ['exchange', 'error_type'],
      registers: [this.register]
    });

    this.wsMessageProcessingDuration = new promClient.Histogram({
      name: 'ws_collector_message_processing_duration_seconds',
      help: 'WebSocket message processing duration in seconds',
      labelNames: ['exchange', 'type'],
      buckets: [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5],
      registers: [this.register]
    });

    // 交易數據指標
    this.tradesCollectedTotal = new promClient.Counter({
      name: 'ws_collector_trades_collected_total',
      help: 'Total number of trades collected',
      labelNames: ['exchange', 'symbol'],
      registers: [this.register]
    });

    this.tradesQueueSize = new promClient.Gauge({
      name: 'ws_collector_trades_queue_size',
      help: 'Current trades queue size',
      labelNames: ['exchange'],
      registers: [this.register]
    });

    // 訂單簿指標
    this.orderbookUpdatesTotal = new promClient.Counter({
      name: 'ws_collector_orderbook_updates_total',
      help: 'Total number of orderbook updates',
      labelNames: ['exchange', 'symbol'],
      registers: [this.register]
    });

    this.orderbookSnapshotsTotal = new promClient.Counter({
      name: 'ws_collector_orderbook_snapshots_total',
      help: 'Total number of orderbook snapshots',
      labelNames: ['exchange', 'symbol'],
      registers: [this.register]
    });

    this.orderbookQueueSize = new promClient.Gauge({
      name: 'ws_collector_orderbook_queue_size',
      help: 'Current orderbook queue size',
      labelNames: ['exchange'],
      registers: [this.register]
    });

    this.orderbookBestBidPrice = new promClient.Gauge({
      name: 'ws_collector_orderbook_best_bid_price',
      help: 'Best bid price in orderbook',
      labelNames: ['exchange', 'symbol'],
      registers: [this.register]
    });

    this.orderbookBestAskPrice = new promClient.Gauge({
      name: 'ws_collector_orderbook_best_ask_price',
      help: 'Best ask price in orderbook',
      labelNames: ['exchange', 'symbol'],
      registers: [this.register]
    });

    this.orderbookSpread = new promClient.Gauge({
      name: 'ws_collector_orderbook_spread',
      help: 'Orderbook spread (best ask - best bid)',
      labelNames: ['exchange', 'symbol'],
      registers: [this.register]
    });

    this.orderbookSpreadBps = new promClient.Gauge({
      name: 'ws_collector_orderbook_spread_bps',
      help: 'Orderbook spread in basis points',
      labelNames: ['exchange', 'symbol'],
      registers: [this.register]
    });

    // Redis 指標
    this.redisQueuePushTotal = new promClient.Counter({
      name: 'ws_collector_redis_queue_push_total',
      help: 'Total number of messages pushed to Redis queue',
      labelNames: ['queue_type'],
      registers: [this.register]
    });

    this.redisQueueErrors = new promClient.Counter({
      name: 'ws_collector_redis_queue_errors_total',
      help: 'Total number of Redis queue errors',
      labelNames: ['queue_type', 'error_type'],
      registers: [this.register]
    });

    this.redisQueueSize = new promClient.Gauge({
      name: 'ws_collector_redis_queue_size',
      help: 'Current Redis queue size',
      labelNames: ['queue_type'],
      registers: [this.register]
    });

    // 資料庫指標
    this.dbFlushedTotal = new promClient.Counter({
      name: 'ws_collector_db_flushed_total',
      help: 'Total number of records flushed to database',
      labelNames: ['table', 'status'],
      registers: [this.register]
    });

    this.dbFlushErrors = new promClient.Counter({
      name: 'ws_collector_db_flush_errors_total',
      help: 'Total number of database flush errors',
      labelNames: ['table'],
      registers: [this.register]
    });

    this.dbFlushDuration = new promClient.Histogram({
      name: 'ws_collector_db_flush_duration_seconds',
      help: 'Database flush duration in seconds',
      labelNames: ['table'],
      buckets: [0.1, 0.5, 1, 2, 5, 10, 30],
      registers: [this.register]
    });

    this.dbIsFlushing = new promClient.Gauge({
      name: 'ws_collector_db_is_flushing',
      help: 'Database is currently flushing (1=yes, 0=no)',
      registers: [this.register]
    });

    // 系統指標
    this.collectorUptime = new promClient.Gauge({
      name: 'ws_collector_uptime_seconds',
      help: 'Collector uptime in seconds',
      registers: [this.register]
    });

    this.collectorRunning = new promClient.Gauge({
      name: 'ws_collector_running',
      help: 'Collector running status (1=running, 0=stopped)',
      registers: [this.register]
    });

    // 設定初始狀態
    this.collectorRunning.set(1);

    log.info('MetricsServer initialized');
  }

  /**
   * 啟動 HTTP server
   */
  public start(): void {
    this.server = http.createServer(async (req, res) => {
      if (req.url === '/metrics') {
        try {
          res.setHeader('Content-Type', this.register.contentType);
          const metrics = await this.register.metrics();
          res.end(metrics);
        } catch (error) {
          res.statusCode = 500;
          res.end('Error generating metrics');
          log.error('Error generating metrics', error);
        }
      } else if (req.url === '/health') {
        res.setHeader('Content-Type', 'application/json');
        res.end(JSON.stringify({ status: 'ok', uptime: process.uptime() }));
      } else {
        res.statusCode = 404;
        res.end('Not found');
      }
    });

    this.server.listen(this.port, () => {
      log.info(`Metrics server listening on port ${this.port}`);
      log.info(`Metrics endpoint: http://localhost:${this.port}/metrics`);
      log.info(`Health endpoint: http://localhost:${this.port}/health`);
    });
  }

  /**
   * 停止 HTTP server
   */
  public stop(): void {
    if (this.server) {
      this.collectorRunning.set(0);
      this.server.close(() => {
        log.info('Metrics server stopped');
      });
    }
  }

  /**
   * 取得 registry（用於測試）
   */
  public getRegister(): promClient.Registry {
    return this.register;
  }
}

// 全局 metrics server 實例（單例模式）
let metricsServerInstance: MetricsServer | null = null;

export function getMetricsServer(port: number = 8001): MetricsServer {
  if (!metricsServerInstance) {
    metricsServerInstance = new MetricsServer(port);
  }
  return metricsServerInstance;
}
