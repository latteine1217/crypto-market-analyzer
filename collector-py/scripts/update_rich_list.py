import os
import sys
import logging
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))
from connectors.bitinfocharts import BitInfoChartsClient

# Load environment variables
load_dotenv()
# Also load from parent directory if needed
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        database=os.getenv('POSTGRES_DB', 'crypto_db'),
        user=os.getenv('POSTGRES_USER', 'crypto'),
        password=os.getenv('POSTGRES_PASSWORD', 'crypto_pass')
    )

def main():
    logger.info("Starting Rich List update...")
    client = BitInfoChartsClient()
    stats = client.fetch_distribution_data()
    
    if not stats:
        logger.error("Failed to fetch rich list data")
        sys.exit(1)
        
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get Blockchain ID for BTC
        cur.execute("SELECT id FROM blockchains WHERE name = 'BTC'")
        res = cur.fetchone()
        if not res:
            logger.error("BTC blockchain not found in DB. Inserting default...")
            # Insert default if missing (should be there from migration)
            cur.execute("INSERT INTO blockchains (name, full_name, native_token) VALUES ('BTC', 'Bitcoin', 'BTC') RETURNING id")
            blockchain_id = cur.fetchone()[0]
        else:
            blockchain_id = res[0]
        
        timestamp = datetime.now()
        
        inserted_count = 0
        for row in stats:
            cur.execute("""
                INSERT INTO rich_list_stats 
                (snapshot_date, blockchain_id, symbol, rank_group, address_count, total_balance, total_balance_usd, percentage_of_supply, data_source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'bitinfocharts')
            """, (
                timestamp,
                blockchain_id,
                row['symbol'],
                row['rank_group'],
                row['address_count'],
                row['total_balance'],
                row['total_balance_usd'],
                row['percentage_of_supply']
            ))
            inserted_count += 1
            
        conn.commit()
        logger.info(f"Successfully inserted {inserted_count} rich list records for BTC")
        
    except Exception as e:
        logger.error(f"Database error: {e}")
        if 'conn' in locals() and conn:
            conn.rollback()
    finally:
        if 'cur' in locals() and cur:
            cur.close()
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    main()
