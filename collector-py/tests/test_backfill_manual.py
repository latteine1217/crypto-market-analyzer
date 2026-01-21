#!/usr/bin/env python3
"""
手動測試回填機制
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from loguru import logger
from orchestrator import DataOrchestrator
from tasks.maintenance_tasks import run_backfill_task

logger.info("🧪 Manual backfill test starting...")

# 初始化 Orchestrator
orchestrator = DataOrchestrator()

logger.info("📊 Running backfill task manually...")
try:
    run_backfill_task(orchestrator)
    logger.success("✅ Backfill task completed")
except Exception as e:
    logger.error(f"❌ Backfill task failed: {e}", exc_info=True)

logger.info("🏁 Test finished")
