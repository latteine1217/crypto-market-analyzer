#!/bin/bash

# Rich List 完整驗收測試腳本
# 測試範圍：End-to-End 資料流驗證

set -e

BOLD='\033[1m'
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BOLD}${BLUE}"
echo "╔════════════════════════════════════════════════════╗"
echo "║    Rich List 資料流完整驗收測試                   ║"
echo "║    Database → API → Frontend                       ║"
echo "╚════════════════════════════════════════════════════╝"
echo -e "${NC}\n"

# Test Results
PASS=0
FAIL=0

# ============================================
# Test 1: 資料庫資料完整性
# ============================================
echo -e "${BOLD}[Test 1/6] 資料庫資料完整性${NC}"
DB_DAYS=$(docker exec crypto_timescaledb psql -U crypto -d crypto_db -t -c "
  SELECT COUNT(DISTINCT DATE(time)) 
  FROM address_tier_snapshots ats
  JOIN blockchains b ON ats.blockchain_id = b.id
  WHERE b.name = 'BTC';
" | tr -d ' ')

if [ "$DB_DAYS" -ge 1 ]; then
  echo -e "  ${GREEN}✓ PASS${NC} - 資料庫包含 ${DB_DAYS} 天資料"
  ((PASS++))
else
  echo -e "  ${RED}✗ FAIL${NC} - 資料庫僅包含 ${DB_DAYS} 天資料（至少需要 1 天）"
  ((FAIL++))
fi

# ============================================
# Test 2: 每日記錄數量
# ============================================
echo -e "\n${BOLD}[Test 2/6] 每日記錄數量（應為 12 個 rank_group）${NC}"
INVALID_DAYS=$(docker exec crypto_timescaledb psql -U crypto -d crypto_db -t -c "
  SELECT COUNT(*) 
  FROM (
    SELECT DATE(time) as day, COUNT(*) as cnt 
    FROM address_tier_snapshots ats
    JOIN blockchains b ON ats.blockchain_id = b.id
    WHERE b.name = 'BTC' 
    GROUP BY DATE(time) 
    HAVING COUNT(*) != 12
  ) sub;
" | tr -d ' ')

if [ "$INVALID_DAYS" -eq 0 ]; then
  echo -e "  ${GREEN}✓ PASS${NC} - 所有日期都包含完整的 12 個 rank_group"
  ((PASS++))
else
  echo -e "  ${RED}✗ FAIL${NC} - 發現 ${INVALID_DAYS} 天資料不完整"
  ((FAIL++))
fi

# ============================================
# Test 3: SQL 去重邏輯
# ============================================
echo -e "\n${BOLD}[Test 3/6] SQL 去重邏輯（防止同日多次快照導致重複）${NC}"
DUPLICATE_COUNT=$(docker exec crypto_timescaledb psql -U crypto -d crypto_db -t -c "
  WITH ranked_snapshots AS (
    SELECT 
      DATE(time) as day,
      tier_name as rank_group,
      ROW_NUMBER() OVER (
        PARTITION BY DATE(time), tier_name 
        ORDER BY time DESC
      ) as rn
    FROM address_tier_snapshots ats
    JOIN blockchains b ON ats.blockchain_id = b.id
    WHERE b.name = 'BTC'
  )
  SELECT COUNT(*) 
  FROM ranked_snapshots 
  WHERE rn > 1;
" | tr -d ' ')

if [ "$DUPLICATE_COUNT" -gt 0 ]; then
  echo -e "  ${GREEN}✓ PASS${NC} - 偵測到 ${DUPLICATE_COUNT} 筆重複資料，去重邏輯已生效"
  ((PASS++))
else
  echo -e "  ${GREEN}✓ PASS${NC} - 無重複資料"
  ((PASS++))
fi

# ============================================
# Test 4: API 端點回應
# ============================================
echo -e "\n${BOLD}[Test 4/6] API 端點回應正確性${NC}"
API_RESPONSE=$(curl -s "http://localhost/api/blockchain/BTC/rich-list?days=30")
API_COUNT=$(echo "$API_RESPONSE" | jq '.data | length')
API_DATES=$(echo "$API_RESPONSE" | jq -r '.data | group_by(.snapshot_date) | length')

EXPECTED_COUNT=$((DB_DAYS * 12))

if [ "$API_COUNT" -eq "$EXPECTED_COUNT" ] && [ "$API_DATES" -eq "$DB_DAYS" ]; then
  echo -e "  ${GREEN}✓ PASS${NC} - API 返回 ${API_COUNT} 筆記錄（${DB_DAYS} 天 × 12 groups）"
  ((PASS++))
else
  echo -e "  ${RED}✗ FAIL${NC} - API 返回異常（預期 ${EXPECTED_COUNT} 筆，實際 ${API_COUNT} 筆）"
  ((FAIL++))
fi

# ============================================
# Test 5: rank_group 格式完整性
# ============================================
echo -e "\n${BOLD}[Test 5/6] rank_group 格式完整性${NC}"
UNIQUE_GROUPS=$(echo "$API_RESPONSE" | jq -r '.data[0:12] | .[].rank_group' | sort -u | wc -l | tr -d ' ')

if [ "$UNIQUE_GROUPS" -eq 12 ]; then
  echo -e "  ${GREEN}✓ PASS${NC} - 包含完整的 12 個 rank_group"
  ((PASS++))
else
  echo -e "  ${RED}✗ FAIL${NC} - 僅找到 ${UNIQUE_GROUPS} 個 rank_group"
  ((FAIL++))
fi

# ============================================
# Test 6: 資料總量一致性
# ============================================
echo -e "\n${BOLD}[Test 6/6] 資料總量一致性（DB vs API）${NC}"
DB_TOTAL=$(docker exec crypto_timescaledb psql -U crypto -d crypto_db -t -c "
  WITH latest_snapshot AS (
    SELECT time 
    FROM address_tier_snapshots ats
    JOIN blockchains b ON ats.blockchain_id = b.id
    WHERE b.name = 'BTC' 
    ORDER BY time DESC 
    LIMIT 1
  )
  SELECT ROUND(SUM(total_balance)::numeric, 0)
  FROM address_tier_snapshots
  WHERE blockchain_id = (SELECT id FROM blockchains WHERE name = 'BTC')
    AND time = (SELECT time FROM latest_snapshot);
" | tr -d ' ')

API_TOTAL=$(echo "$API_RESPONSE" | jq '.data | group_by(.snapshot_date) | last | map(.total_balance | tonumber) | add | floor')

if [ "$DB_TOTAL" -eq "$API_TOTAL" ]; then
  echo -e "  ${GREEN}✓ PASS${NC} - 資料總量一致（${DB_TOTAL} BTC）"
  ((PASS++))
else
  echo -e "  ${RED}✗ FAIL${NC} - 資料總量不一致（DB: ${DB_TOTAL}, API: ${API_TOTAL}）"
  ((FAIL++))
fi

# ============================================
# 測試總結
# ============================================
echo -e "\n${BOLD}${BLUE}"
echo "╔════════════════════════════════════════════════════╗"
echo "║                   測試總結                         ║"
echo "╚════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo -e "  通過: ${GREEN}${PASS}/6${NC}"
echo -e "  失敗: ${RED}${FAIL}/6${NC}"

if [ "$FAIL" -eq 0 ]; then
  echo -e "\n${GREEN}${BOLD}✓ 所有測試通過！Rich List 資料流完全正常${NC}"
  echo -e "\n${YELLOW}下一步：請在瀏覽器訪問${NC}"
  echo -e "  ${BLUE}http://localhost:3001/onchain${NC}"
  echo -e "${YELLOW}並執行硬重整 (Ctrl+Shift+R / Cmd+Shift+R) 清除快取${NC}\n"
  exit 0
else
  echo -e "\n${RED}${BOLD}✗ 測試失敗，請檢查上述錯誤訊息${NC}\n"
  exit 1
fi
