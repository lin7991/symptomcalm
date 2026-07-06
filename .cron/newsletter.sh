#!/bin/bash
# SymptomCalm Weekly Newsletter — fires every Saturday 07:00
# Reads subscribers from Cloudflare KV, compiles weekly content digest, sends via Resend

PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$HOME/.local/bin"
cd "$HOME/symptomcalm" || exit 1

LOG_FILE="$HOME/symptomcalm/.cron/outreach/newsletter.log"
echo "$(date): Newsletter run starting" >> "$LOG_FILE"

# 1. Get subscriber emails from Cloudflare KV via Worker API
# The Worker needs a GET endpoint for admin. For now, use the KV directly if available,
# or maintain a local subscriber file as fallback.
SUBSCRIBERS_FILE="$HOME/symptomcalm/.cron/.subscribers.json"

if [ ! -f "$SUBSCRIBERS_FILE" ]; then
  echo "[]" > "$SUBSCRIBERS_FILE"
  echo "  No subscribers yet" >> "$LOG_FILE"
fi

SUBSCRIBERS=$(python3 -c "
import json
with open('$SUBSCRIBERS_FILE') as f:
    subs = json.load(f)
for s in subs:
    print(s.get('email', ''))
" 2>/dev/null)

if [ -z "$SUBSCRIBERS" ]; then
  echo "$(date): No subscribers to send to" >> "$LOG_FILE"
  exit 0
fi

# 2. Compile this week's article digest
DIGEST=$(git log --since="$(date -v-7d '+%Y-%m-%d')" --oneline --format="  - %s" 2>/dev/null | head -20)
ARTICLE_COUNT=$(echo "$DIGEST" | wc -l | tr -d ' ')

# 3. Build email HTML
EMAIL_HTML=$(cat << EMAIL
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,sans-serif;max-width:600px;margin:0 auto;padding:20px;color:#333;">
  <div style="text-align:center;padding:20px 0;border-bottom:2px solid #2C7A7B;">
    <h1 style="color:#1A535C;margin:0;">SymptomCalm</h1>
    <p style="color:#718096;font-size:14px;">Weekly Digest</p>
  </div>
  <div style="padding:20px 0;">
    <p>Hi there,</p>
    <p>Here's what we published on SymptomCalm this week:</p>
    <ul style="line-height:1.8;color:#2C7A7B;">
      $(echo "$DIGEST" | sed 's/- /<li>/' | sed 's/$/<\/li>/')
    </ul>
    <p style="margin-top:20px;">
      <a href="https://symptomcalm.com/" style="display:inline-block;background:#2C7A7B;color:white;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:600;">Read the Latest</a>
    </p>
  </div>
  <div style="border-top:1px solid #E2E8F0;padding:20px 0;font-size:12px;color:#A0AEC0;text-align:center;">
    <p>You're receiving this because you subscribed to SymptomCalm updates.</p>
    <p><a href="mailto:contact@symptomcalm.com?subject=Unsubscribe" style="color:#A0AEC0;">Unsubscribe</a></p>
  </div>
</body>
</html>
EMAIL
)

# 4. Send via Resend API
API_KEY=$(grep api_key "$HOME/symptomcalm/.cron/.smtp_config" 2>/dev/null | cut -d= -f2)
if [ -z "$API_KEY" ]; then
  echo "$(date): ERROR - No Resend API key" >> "$LOG_FILE"
  exit 1
fi

SENT=0
for email in $SUBSCRIBERS; do
  if [ -z "$email" ]; then continue; fi
  curl -s --max-time 15 -X POST "https://api.resend.com/emails" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d "$(python3 -c "
import json
print(json.dumps({
    'from': 'SymptomCalm <contact@symptomcalm.com>',
    'to': ['$email'],
    'subject': 'SymptomCalm Weekly - $ARTICLE_COUNT new articles this week',
    'html': '''$EMAIL_HTML'''
}))")" 2>/dev/null
  SENT=$((SENT + 1))
  sleep 1  # Rate limit
done

echo "$(date): Newsletter sent to $SENT subscribers ($ARTICLE_COUNT articles)" >> "$LOG_FILE"
