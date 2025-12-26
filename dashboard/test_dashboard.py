"""
Dashboard 功能測試腳本
"""
import sys
from pathlib import Path

# 測試 1: 匯入檢查
print("=" * 80)
print("測試 1: 檢查依賴套件")
print("=" * 80)

required_packages = [
    ('dash', 'Dash'),
    ('dash_bootstrap_components', 'Dash Bootstrap Components'),
    ('plotly', 'Plotly'),
    ('pandas', 'Pandas'),
    ('psycopg2', 'PostgreSQL Driver'),
]

all_ok = True
for package, name in required_packages:
    try:
        __import__(package)
        print(f"✅ {name}")
    except ImportError:
        print(f"❌ {name} - 未安裝")
        all_ok = False

if not all_ok:
    print("\n請執行: pip install -r requirements.txt")
    sys.exit(1)

# 測試 2: 資料載入器
print("\n" + "=" * 80)
print("測試 2: 資料載入器")
print("=" * 80)

try:
    from data_loader import DataLoader
    loader = DataLoader()
    print("✅ DataLoader 初始化成功")

    # 測試資料庫連接
    df = loader.get_latest_prices(limit=3)
    if not df.empty:
        print(f"✅ 成功讀取 {len(df)} 筆最新價格")
        print("\n最新價格：")
        for _, row in df.iterrows():
            print(f"  {row['exchange']:8} {row['symbol']:10} ${row['price']:>10,.2f}")
    else:
        print("⚠️  沒有價格資料（可能 collector 尚未運行）")

except Exception as e:
    print(f"❌ 資料載入器測試失敗: {e}")
    import traceback
    traceback.print_exc()

# 測試 3: 頁面模組
print("\n" + "=" * 80)
print("測試 3: 頁面模組")
print("=" * 80)

pages = ['overview', 'technical', 'signals', 'liquidity']
for page in pages:
    try:
        module = __import__(f'pages.{page}', fromlist=[page])
        if hasattr(module, 'layout'):
            print(f"✅ {page}.py - layout 存在")
        else:
            print(f"⚠️  {page}.py - layout 不存在")
    except Exception as e:
        print(f"❌ {page}.py - 載入失敗: {e}")

# 測試 4: 主應用
print("\n" + "=" * 80)
print("測試 4: 主應用程式")
print("=" * 80)

try:
    # 不實際啟動，只檢查能否匯入
    import app
    print("✅ app.py 可正常匯入")
    print(f"✅ 應用名稱: {app.app.title}")
except Exception as e:
    print(f"❌ app.py 匯入失敗: {e}")

# 總結
print("\n" + "=" * 80)
print("測試總結")
print("=" * 80)
print("\n✅ Dashboard 核心功能測試完成")
print("\n啟動 Dashboard:")
print("  python3 app.py")
print("\n或使用啟動腳本:")
print("  ./start.sh")
print("\n訪問網址:")
print("  http://localhost:8050")
print("\n" + "=" * 80)
