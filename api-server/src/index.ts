import express from 'express';
import { createServer } from 'http';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import dotenv from 'dotenv';
import { logger } from './utils/logger';
import { errorHandler } from './middleware/errorHandler';
import { marketRoutes } from './routes/markets';
import { ohlcvRoutes } from './routes/ohlcv';
import { orderbookRoutes } from './routes/orderbook';
import { derivativesRoutes } from './routes/derivatives';
import { blockchainRoutes } from './routes/blockchain';
import { alertRoutes } from './routes/alerts';
import { newsRoutes } from './routes/news';
import { analyticsRoutes } from './routes/analytics';
import { eventsRoutes } from './routes/events';
import sentimentRoutes from './routes/sentiment';
import etfRoutes from './routes/etf';
import fredRoutes from './routes/fred';
import { statusRoutes } from './routes/status';
import pool from './database/pool';
import { startAlertMonitor } from './services/alertService';
import { SocketService } from './services/socketService';
import { PostgresTransport } from './utils/PostgresTransport';

import { config } from './shared/config';

// Initialize Database Logging
logger.add(new PostgresTransport({ pool }));

const app = express();
const httpServer = createServer(app);
const PORT = config.server.port;

// Initialize Socket.IO
SocketService.getInstance().initialize(httpServer);

// Middleware
app.use(helmet({
  crossOriginResourcePolicy: { policy: "cross-origin" }
}));
app.use(cors({
  origin: '*',
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));
app.use(compression());
app.use(express.json());

// Health check
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// API Routes
app.use('/api/markets', marketRoutes);
app.use('/api/ohlcv', ohlcvRoutes);
app.use('/api/orderbook', orderbookRoutes);
app.use('/api/derivatives', derivativesRoutes);
app.use('/api/blockchain', blockchainRoutes);
app.use('/api/alerts', alertRoutes);
app.use('/api/news', newsRoutes);
app.use('/api/analytics', analyticsRoutes);
app.use('/api/events', eventsRoutes);
app.use('/api/fear-greed', sentimentRoutes);
app.use('/api/etf-flows', etfRoutes);
app.use('/api/fred', fredRoutes);
app.use('/api/status', statusRoutes);

// Error handling
app.use(errorHandler);

// Start server
(async () => {
  try {
    httpServer.listen(PORT, () => {
      logger.info(`API Server running on port ${PORT}`);
      logger.info(`Environment: ${process.env.NODE_ENV || 'development'}`);
      
      // Start background services
      startAlertMonitor();
    });
  } catch (error) {
    logger.error('Failed to start API Server due to migration error:', error);
    process.exit(1);
  }
})();

// Graceful shutdown
process.on('SIGTERM', () => {
  logger.info('SIGTERM signal received: closing HTTP server');
  process.exit(0);
});

process.on('SIGINT', () => {
  logger.info('SIGINT signal received: closing HTTP server');
  process.exit(0);
});
