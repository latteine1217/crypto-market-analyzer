import { Server as HttpServer } from 'http';
import { Server, Socket } from 'socket.io';
import { logger } from '../utils/logger';

export class SocketService {
  private static instance: SocketService;
  private io: Server | null = null;

  private constructor() {}

  public static getInstance(): SocketService {
    if (!SocketService.instance) {
      SocketService.instance = new SocketService();
    }
    return SocketService.instance;
  }

  public initialize(httpServer: HttpServer) {
    this.io = new Server(httpServer, {
      cors: {
        origin: '*', // Allow all origins for simplicity in this project
        methods: ['GET', 'POST']
      }
    });

    this.io.on('connection', (socket: Socket) => {
      logger.info(`New WebSocket client connected: ${socket.id}`);

      socket.on('disconnect', () => {
        logger.info(`WebSocket client disconnected: ${socket.id}`);
      });
    });

    logger.info('Socket.IO initialized');
  }

  public emit(event: string, data: any) {
    if (this.io) {
      this.io.emit(event, data);
    } else {
      logger.warn('Socket.IO not initialized, cannot emit event');
    }
  }
}
