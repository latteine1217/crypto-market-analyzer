#!/usr/bin/env node

/**
 * 測試前端 rank_group 解析邏輯
 * 模擬 RichListTable.tsx 的資料處理流程
 */

// 模擬 API 回傳的資料結構
const mockData = [
  { rank_group: "(0 - 0.00001)", total_balance: "43.04000000" },
  { rank_group: "[0.00001 - 0.0001)", total_balance: "516.04000000" },
  { rank_group: "[0.0001 - 0.001)", total_balance: "5177.00000000" },
  { rank_group: "[0.001 - 0.01)", total_balance: "43609.00000000" },
  { rank_group: "[0.01 - 0.1)", total_balance: "272737.00000000" },
  { rank_group: "[0.1 - 1)", total_balance: "1067057.00000000" },
  { rank_group: "[1 - 10)", total_balance: "2044063.00000000" },
  { rank_group: "[10 - 100)", total_balance: "4235270.00000000" },
  { rank_group: "[100 - 1,000)", total_balance: "5155991.00000000" },
  { rank_group: "[1,000 - 10,000)", total_balance: "4288505.00000000" },
  { rank_group: "[10,000 - 100,000)", total_balance: "2195268.00000000" },
  { rank_group: "[100,000 - 1,000,000)", total_balance: "664960.00000000" },
];

// 前端目標層級定義（從 RichListTable.tsx）
const TARGET_TIERS = [
  { label: '(0-1) Coins', min: 0, max: 1 },
  { label: '(1-10) Coins', min: 1, max: 10 },
  { label: '(10-100) Coins', min: 10, max: 100 },
  { label: '(100-1K) Coins', min: 100, max: 1000 },
  { label: '(1K-10K) Coins', min: 1000, max: 10000 },
  { label: '(10K-100K) Coins', min: 10000, max: 100000 },
  { label: '(100K-1M) Coins', min: 100000, max: Infinity },
];

// 前端解析邏輯（與 RichListTable.tsx:86-98 一致）
function parseRankGroup(rankGroup) {
  const clean = rankGroup.replace(/,/g, '');
  const match = clean.match(/^[\(\[](\d+(?:\.\d+)?)\s*-/);
  const rangeMin = match ? parseFloat(match[1]) : 0;
  return rangeMin;
}

// 聚合計算
console.log('\n=== Frontend Parsing Test ===\n');
console.log('Tier Aggregation Results:\n');

TARGET_TIERS.forEach(tier => {
  const total = mockData.reduce((sum, stat) => {
    const rangeMin = parseRankGroup(stat.rank_group);
    
    // 判斷是否屬於當前目標層級
    if (rangeMin >= tier.min && (tier.max === Infinity || rangeMin < tier.max)) {
      console.log(`  ✓ ${stat.rank_group.padEnd(25)} → ${tier.label.padEnd(20)} (parsed: ${rangeMin})`);
      return sum + Number(stat.total_balance);
    }
    return sum;
  }, 0);
  
  console.log(`  → Total for ${tier.label}: ${total.toLocaleString()} BTC\n`);
});

// 驗證是否所有 rank_group 都被正確歸類
console.log('\n=== Verification ===\n');
const totalFromApi = mockData.reduce((sum, stat) => sum + Number(stat.total_balance), 0);
const totalFromTiers = TARGET_TIERS.reduce((sum, tier) => {
  return sum + mockData.reduce((tierSum, stat) => {
    const rangeMin = parseRankGroup(stat.rank_group);
    if (rangeMin >= tier.min && (tier.max === Infinity || rangeMin < tier.max)) {
      return tierSum + Number(stat.total_balance);
    }
    return tierSum;
  }, 0);
}, 0);

console.log(`API Total:   ${totalFromApi.toLocaleString()} BTC`);
console.log(`Tiers Total: ${totalFromTiers.toLocaleString()} BTC`);
console.log(totalFromApi === totalFromTiers ? '✓ Parsing logic is correct!' : '✗ Parsing logic has errors!');
