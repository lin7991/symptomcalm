#!/bin/bash
# SymptomCalm Daily Report — runs at 10:00 every day
# Reports: new articles published, queue status, site health, basic traffic

export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$HOME/.local/bin"
REPORT_DIR="$HOME/symptomcalm/.cron/reports"
mkdir -p "$REPORT_DIR"
REPORT_FILE="$REPORT_DIR/report-$(date +%Y%m%d).md"

{
echo "# 📊 SymptomCalm 每日报告"
echo "**$(date '+%Y-%m-%d %H:%M %A')**"
echo ""

# --- 最近24小时发布内容 ---
echo "## 📝 最近发布"
echo ""
cd "$HOME/symptomcalm" 2>/dev/null || { echo "目录不存在"; exit 1; }

YESTERDAY=$(date -v-1d +%Y-%m-%d)
RECENT=$(git log --since="$YESTERDAY" --oneline --format="  - %s (%ar)" 2>/dev/null)
if [ -n "$RECENT" ]; then
  echo "$RECENT"
else
  echo "  过去24小时无新发布"
fi
echo ""

# --- 队列状态 ---
echo "## 📋 内容队列"
echo ""
STATUS=$(python3 .cron/publish-article.py status 2>/dev/null)
echo "  $STATUS"
PUBLISHED_COUNT=$(python3 -c "import json; d=json.load(open('$HOME/symptomcalm/.content-queue.json')); print(len(d['published']))" 2>/dev/null)
QUEUE_COUNT=$(python3 -c "import json; d=json.load(open('$HOME/symptomcalm/.content-queue.json')); print(len(d['queue']))" 2>/dev/null)
echo "  已发布: $PUBLISHED_COUNT 篇  |  待发布: $QUEUE_COUNT 篇"
echo ""

# --- 站点健康检查 ---
echo "## 🏥 站点健康"
echo ""
ALL_OK=true
for url in \
  "https://symptomcalm.com/" \
  "https://symptomcalm.com/symptoms/anxiety/" \
  "https://symptomcalm.com/symptoms/back-pain/" \
  "https://symptomcalm.com/symptoms/insomnia/" \
  "https://symptomcalm.com/tcm-basics/what-is-qi/" \
  "https://symptomcalm.com/tcm-basics/yin-yang-explained/" \
  "https://symptomcalm.com/tcm-basics/how-acupuncture-works/" \
  "https://symptomcalm.com/symptoms/anxiety/liver-qi-stagnation/" \
  "https://symptomcalm.com/about/" \
  "https://symptomcalm.com/sitemap.xml"; do
  STATUS_CODE=$(curl -sI -o /dev/null -w '%{http_code}' "$url" --connect-timeout 10 2>/dev/null)
  if [ "$STATUS_CODE" = "200" ]; then
    echo "  ✅ $url"
  else
    echo "  ❌ $url → HTTP $STATUS_CODE"
    ALL_OK=false
  fi
done
echo ""
if $ALL_OK; then
  echo "  ✅ 全部页面正常"
else
  echo "  ⚠️ 有页面异常，请检查"
fi
echo ""

# --- Git 状态 ---
echo "## 🔧 Git 仓库"
echo ""
echo "  $(cd ~/symptomcalm && git log --oneline -1)"
echo "  $(cd ~/symptomcalm && git status -sb | head -1)"
echo ""

# --- 流量统计（通过 Cloudflare API）---
echo "## 📈 流量概览"
echo ""
CF_TOKEN_FILE="$HOME/symptomcalm/.cron/.cf_token"
if [ -f "$CF_TOKEN_FILE" ]; then
  CF_TOKEN=$(cat "$CF_TOKEN_FILE")
else
  echo "  无法获取流量数据（CF token 文件不存在）"
  echo "  建议：在 Cloudflare Dashboard 查看 analytics"
  echo ""
  echo "---"
  echo "*报告由 SymptomCalm Auto-Reporter 自动生成*"
  exit 0
fi
CF_ZONE_ID=$(curl -s -H "Authorization: Bearer $CF_TOKEN" \
  "https://api.cloudflare.com/client/v4/zones?name=symptomcalm.com" 2>/dev/null | \
  python3 -c "import json,sys; d=json.load(sys.stdin); print(d['result'][0]['id'])" 2>/dev/null)

if [ -n "$CF_ZONE_ID" ]; then
  YESTERDAY_DATE=$(date -v-1d +%Y-%m-%d)
  TODAY_DATE=$(date +%Y-%m-%d)
  
  # Get analytics for the last 24 hours
  ANALYTICS=$(curl -s -H "Authorization: Bearer $CF_TOKEN" \
    "https://api.cloudflare.com/client/v4/zones/$CF_ZONE_ID/analytics/dashboard" 2>/dev/null)
  
  REQUESTS=$(echo "$ANALYTICS" | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    if d.get('success'):
        r = d['result']['totals']['requests']['all']
        print(r)
    else:
        print('N/A')
except: print('N/A')" 2>/dev/null)
  
  BANDWIDTH=$(echo "$ANALYTICS" | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    if d.get('success'):
        b = d['result']['totals']['bandwidth']['all']
        print(f'{b/1024/1024:.1f} MB')
    else:
        print('N/A')
except: print('N/A')" 2>/dev/null)

  echo "  请求数: ${REQUESTS:-N/A}"
  echo "  带宽: ${BANDWIDTH:-N/A}"
  
  # Top URLs (simplified)
  echo "  数据来源: Cloudflare Analytics"
else
  echo "  无法获取流量数据（CF API 未配置或域名未识别）"
  echo "  建议：在 Cloudflare Dashboard 查看 analytics"
fi
echo ""

# --- Sitemap URL 数量 ---
echo "## 🔗 Sitemap"
echo ""
SITEMAP_COUNT=$(curl -s 'https://symptomcalm.com/sitemap.xml' 2>/dev/null | grep -c '<loc>' || echo 0)
echo "  收录 URL: $SITEMAP_COUNT 个"
echo ""

echo "---"
echo "*报告由 SymptomCalm Auto-Reporter 自动生成*"

} > "$REPORT_FILE"

# Output to stdout for delivery
cat "$REPORT_FILE"
