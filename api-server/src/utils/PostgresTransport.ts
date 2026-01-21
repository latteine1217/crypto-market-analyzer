import Transport, { TransportStreamOptions } from 'winston-transport';
import { Pool } from 'pg';

interface PostgresTransportOptions extends TransportStreamOptions {
  pool: Pool;
}

export class PostgresTransport extends Transport {
  private pool: Pool;

  constructor(opts: PostgresTransportOptions) {
    super(opts);
    this.pool = opts.pool;
  }

  log(info: any, callback: () => void) {
    setImmediate(() => {
      this.emit('logged', info);
    });

    const { level, message, timestamp, value, ...meta } = info;
    
    // Default to 'api' module, allow override in meta
    const moduleName = meta.module || 'api';
    
    // Clean up meta to remove transport-specific properties if any
    const metadata = { ...meta };
    delete metadata.module;
    
    // Ensure timestamp matches DB expectation (ISO string)
    const time = timestamp || new Date().toISOString();

    const queryText = `
      INSERT INTO system_logs (time, module, level, message, value, metadata)
      VALUES ($1, $2, $3, $4, $5, $6)
    `;

    const values = [
      time,
      moduleName,
      level.toUpperCase(),
      message,
      value || null, // Allow passing numerical value for quality metrics
      Object.keys(metadata).length > 0 ? JSON.stringify(metadata) : null
    ];

    // Only log WARN and ERROR levels to DB to avoid spamming
    if (level === 'info' || level === 'debug') {
        callback();
        return;
    }

    this.pool.query(queryText, values)
      .then(() => {
        callback();
      })
      .catch((err) => {
        // Prevent infinite loop if DB logging fails by using console directly
        console.error('Failed to save log to database:', err);
        callback();
      });
  }
}
