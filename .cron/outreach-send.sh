#!/bin/bash
# SymptomCalm Link Outreach — fired by launchd every 8 hours
# Monthly cap: 95 emails

PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$HOME/.local/bin"
cd "$HOME/symptomcalm" || exit 1

# Monthly cap check - count emails sent this month
MONTH=$(date +%Y-%m)
SENT_COUNT=$(python3 -c "
import json
with open('.cron/outreach/sent.json') as f:
    sent = json.load(f)
month_count = sum(1 for info in sent.values()
    if info.get('status') == 'sent' and info.get('sent_at','').startswith('$MONTH'))
print(month_count)
" 2>/dev/null || echo 0)

if [ "$SENT_COUNT" -ge 95 ]; then
  echo "$(date): Monthly cap reached ($SENT_COUNT/95). Skipping." >> "$HOME/symptomcalm/.cron/outreach/send.log"
  exit 0
fi

python3 .cron/outreach.py send 2>&1 >> "$HOME/symptomcalm/.cron/outreach/send.log"
echo "$(date): outreach run complete (monthly: $SENT_COUNT/95)" >> "$HOME/symptomcalm/.cron/outreach/send.log"
