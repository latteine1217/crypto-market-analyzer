import { WSConfig, IWSClient } from './types';
import { BybitWSClient } from './bybit_ws/BybitWSClient';
import { log } from './utils/logger';

export type WSClientConstructor = new (config: WSConfig) => IWSClient;

export class ExchangeRegistry {
  private static clients: Map<string, WSClientConstructor> = new Map();

  static {
    // 註冊預設交易所
    this.register('bybit', BybitWSClient as unknown as WSClientConstructor);
  }

  /**
   * 註冊交易所客戶端
   */
  public static register(name: string, clientClass: WSClientConstructor): void {
    this.clients.set(name.toLowerCase(), clientClass);
    log.info(`Registered exchange client: ${name}`);
  }

  /**
   * 建立交易所客戶端實例
   */
  public static createClient(name: string, config: WSConfig): IWSClient {
    const ClientClass = this.clients.get(name.toLowerCase());
    
    if (!ClientClass) {
      log.error(`Exchange client not found: ${name}. Falling back to Bybit.`);
      const BybitClass = this.clients.get('bybit')!;
      return new BybitClass(config);
    }

    return new ClientClass(config);
  }

  /**
   * 獲取所有已註冊的交易所
   */
  public static getRegisteredExchanges(): string[] {
    return Array.from(this.clients.keys());
  }
}
