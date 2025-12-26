"""
測試新功能
驗證階段 1.1 補齊的所有功能
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

# 添加 src 到路徑
sys.path.insert(0, str(Path(__file__).parent / "src"))

from loguru import logger
from config_loader import ConfigLoader
from loaders.db_loader import DatabaseLoader
from validators.data_validator import DataValidator
from schedulers.backfill_scheduler import BackfillScheduler
from quality_checker import DataQualityChecker
from error_handler import retry_with_backoff, RetryConfig
import ccxt


def test_config_loader():
    """測試配置載入"""
    print("\n" + "=" * 80)
    print("TEST 1: 配置檔載入")
    print("=" * 80)

    try:
        loader = ConfigLoader()
        config = loader.load_collector_config("binance_btcusdt_1m.yml")

        print(f"✅ Config loaded: {config.name}")
        print(f"   Exchange: {config.exchange.name}")
        print(f"   Symbol: {config.symbol.base}/{config.symbol.quote}")
        print(f"   Timeframe: {config.timeframe}")
        print(f"   Request timeout: {config.request.timeout}s")
        print(f"   Max retries: {config.request.max_retries}")
        print(f"   Validation enabled: {config.validation.enabled}")
        print(f"   Quality checks: {', '.join(config.validation.checks)}")

        return True
    except Exception as e:
        print(f"❌ Config loader test failed: {e}")
        return False


def test_data_validator():
    """測試資料驗證"""
    print("\n" + "=" * 80)
    print("TEST 2: 資料驗證器")
    print("=" * 80)

    try:
        validator = DataValidator()

        # 建立測試資料
        base_time = int(datetime.now(timezone.utc).timestamp() * 1000)
        test_ohlcv = [
            [base_time, 50000, 50100, 49900, 50050, 100],
            [base_time + 60000, 50050, 50150, 50000, 50100, 120],
            [base_time + 120000, 50100, 50200, 50050, 50150, 110],
        ]

        result = validator.validate_ohlcv_batch(test_ohlcv, "1m")

        print(f"✅ Validation completed")
        print(f"   Total records: {result['total_records']}")
        print(f"   Valid: {result['valid']}")
        print(f"   Errors: {len(result['errors'])}")
        print(f"   Warnings: {len(result['warnings'])}")

        return True
    except Exception as e:
        print(f"❌ Data validator test failed: {e}")
        return False


def test_backfill_scheduler():
    """測試補資料排程器"""
    print("\n" + "=" * 80)
    print("TEST 3: 補資料排程器")
    print("=" * 80)

    try:
        scheduler = BackfillScheduler()

        # 檢查資料缺失（假設 market_id=1 存在）
        market_id = 1
        timeframe = "1m"
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=1)

        gaps = scheduler.check_data_gaps(
            market_id, timeframe, start_time, end_time
        )

        print(f"✅ Gap detection completed")
        print(f"   Time range: {start_time} - {end_time}")
        print(f"   Gaps found: {len(gaps)}")

        if gaps:
            total_missing = sum(g['missing_count'] for g in gaps)
            print(f"   Total missing records: {total_missing}")
            print(f"   First gap: {gaps[0]['start_time']} - {gaps[0]['end_time']}")

        # 測試任務建立
        if gaps:
            task_id = scheduler.create_backfill_task(
                market_id=market_id,
                data_type='ohlcv',
                timeframe=timeframe,
                start_time=gaps[0]['start_time'],
                end_time=gaps[0]['end_time'],
                priority=10,
                expected_records=gaps[0]['missing_count']
            )
            print(f"   Created test backfill task #{task_id}")

        # 查詢待執行任務
        pending_tasks = scheduler.get_pending_tasks(limit=5)
        print(f"   Pending tasks: {len(pending_tasks)}")

        scheduler.close()
        return True

    except Exception as e:
        print(f"❌ Backfill scheduler test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_quality_checker():
    """測試品質檢查器"""
    print("\n" + "=" * 80)
    print("TEST 4: 資料品質檢查器")
    print("=" * 80)

    try:
        checker = DataQualityChecker()

        # 檢查單一市場（假設 market_id=1 存在）
        result = checker.check_ohlcv_quality(
            market_id=1,
            timeframe="1m",
            lookback_hours=1,
            create_backfill_tasks=False  # 測試時不建立任務
        )

        print(f"✅ Quality check completed")
        print(f"   Total records: {result.get('total_records', 0)}")
        print(f"   Valid: {result.get('valid', False)}")
        print(f"   Errors: {len(result.get('errors', []))}")
        print(f"   Warnings: {len(result.get('warnings', []))}")

        # 生成品質報告
        report = checker.generate_quality_report(market_id=1, hours=24)
        print(f"\n   Quality Report (last 24h):")
        print(f"   - Average score: {report['avg_score']:.2f}")
        print(f"   - Total checks: {report['total_checks']}")
        print(f"   - Failed checks: {report['failed_checks']}")

        checker.close()
        return True

    except Exception as e:
        print(f"❌ Quality checker test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_error_handler():
    """測試錯誤處理與重試機制"""
    print("\n" + "=" * 80)
    print("TEST 5: 錯誤處理與重試機制")
    print("=" * 80)

    try:
        retry_config = RetryConfig(
            max_retries=2,
            initial_delay=0.5,
            backoff_factor=2.0
        )

        attempt_count = [0]  # 使用列表以便在閉包中修改

        @retry_with_backoff(
            config=retry_config,
            retryable_exceptions=(ccxt.NetworkError,),
            log_errors=False
        )
        def flaky_function():
            attempt_count[0] += 1
            print(f"   Attempt {attempt_count[0]}")

            if attempt_count[0] < 2:
                raise ccxt.NetworkError("Simulated network error")

            return "Success!"

        result = flaky_function()

        print(f"✅ Retry mechanism works")
        print(f"   Result: {result}")
        print(f"   Total attempts: {attempt_count[0]}")

        return True

    except Exception as e:
        print(f"❌ Error handler test failed: {e}")
        return False


def test_database_quality_summary():
    """測試品質摘要寫入資料庫"""
    print("\n" + "=" * 80)
    print("TEST 6: 資料庫品質摘要")
    print("=" * 80)

    try:
        db = DatabaseLoader()

        # 建立模擬驗證結果
        validation_result = {
            'valid': True,
            'total_records': 60,
            'errors': [],
            'warnings': [
                {
                    'type': 'price_jump',
                    'count': 2,
                    'details': []
                }
            ]
        }

        # 寫入品質摘要
        summary_id = db.insert_quality_summary(
            market_id=1,
            data_type='ohlcv',
            timeframe='1m',
            time_range_start=datetime.now(timezone.utc) - timedelta(hours=1),
            time_range_end=datetime.now(timezone.utc),
            total_records=60,
            validation_result=validation_result
        )

        print(f"✅ Quality summary inserted")
        print(f"   Summary ID: {summary_id}")

        db.close()
        return True

    except Exception as e:
        print(f"❌ Database quality summary test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """執行所有測試"""
    print("\n" + "=" * 80)
    print("階段 1.1 功能驗證測試")
    print("=" * 80)

    tests = [
        ("配置載入", test_config_loader),
        ("資料驗證", test_data_validator),
        ("補資料排程", test_backfill_scheduler),
        ("品質檢查", test_quality_checker),
        ("錯誤處理", test_error_handler),
        ("品質摘要DB", test_database_quality_summary),
    ]

    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            logger.error(f"Test '{name}' crashed: {e}")
            results[name] = False

    # 總結
    print("\n" + "=" * 80)
    print("測試總結")
    print("=" * 80)

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")

    print(f"\n總計: {passed}/{total} 測試通過")

    if passed == total:
        print("\n🎉 所有測試通過！階段 1.1 功能補齊完成。")
    else:
        print(f"\n⚠️ {total - passed} 個測試失敗，需要修復。")


if __name__ == "__main__":
    main()
