import express from 'express';
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
import { startAlertMonitor } from './services/alertService';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 8080;

// Middleware
app.use(helmet());
app.use(cors());
app.use(compression());
app.use(express.json());

// Health check
app.get('/health', (req, res) => {
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

// Error handling
app.use(errorHandler);

// Start server
app.listen(PORT, () => {
  logger.info(`API Server running on port ${PORT}`);
  logger.info(`Environment: ${process.env.NODE_ENV || 'development'}`);
  
  // Start background services
  startAlertMonitor();
});

// Graceful shutdown
process.on('SIGTERM', () => {
  logger.info('SIGTERM signal received: closing HTTP server');
  process.exit(0);
});

process.on('SIGINT', () => {
  logger.info('SIGINT signal received: closing HTTP server');
  process.exit(0);
});
