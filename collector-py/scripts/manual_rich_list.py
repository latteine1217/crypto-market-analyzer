import sys
import os
from pathlib import Path
sys.path.insert(0, '/app/src')

from config_loader import ConfigLoader
from loaders.db_loader import DatabaseLoader
from validators.data_validator import DataValidator
from metrics_exporter import CollectorMetrics
from orchestrator import CollectorOrchestrator
from tasks.external_tasks import run_rich_list_task
from loguru import logger

# Setup minimal logger to stdout
logger.remove()
logger.add(sys.stdout, level="INFO")

def manual_run():
    try:
        logger.info("Initializing Orchestrator...")
        config_loader = ConfigLoader()
        configs = config_loader.load_all_collector_configs()
        db = DatabaseLoader()
        validator = DataValidator()
        metrics = CollectorMetrics() 
        orchestrator = CollectorOrchestrator(configs, db, validator, metrics)

        logger.info("Executing Rich List Task...")
        run_rich_list_task(orchestrator)
        logger.info("Task Completed Successfully.")
        
    except Exception as e:
        logger.error(f"Execution failed: {e}")

if __name__ == "__main__":
    manual_run()
