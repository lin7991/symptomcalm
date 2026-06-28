#!/bin/bash
# SymptomCalm auto-publisher — fired by launchd every 3 hours
# Uses hermes chat in one-shot mode to generate and publish content

export HERMES_HOME="$HOME/.hermes"
export PATH="/usr/local/bin:/opt/homebrew/bin:$HOME/.local/bin:$PATH"

cd "$HOME/symptomcalm" || exit 1

# Check remaining — if 0, still run Hermes to refill
REMAINING=$(python3 .cron/publish-article.py remaining 2>/dev/null)
echo "$(date): Queue has $REMAINING items" >> "$HOME/symptomcalm/.cron/publish.log"

# Run Hermes in one-shot to refill if needed, then publish
hermes chat --profile symptomcalm -Q -q "
You are in ~/symptomcalm.

STEP 1: Check queue with 'python3 .cron/publish-article.py remaining'.
If remaining < 5, you need to refill first:
  - Generate 15 new article ideas (mix of: new clusters under existing symptoms, 
    new pillars like allergies/women-health/skin, TCM basics, treatments)
  - Format as JSON array with title/path/type/parent/estimated_read_time/keywords
  - Pipe to: echo '[...]' | python3 .cron/publish-article.py add

STEP 2: Read next item with 'python3 .cron/publish-article.py next'.
Generate a complete HTML article using .cron/article-template.html.
Write to /tmp/symptomcalm-article.html.
Run 'python3 .cron/publish-article.py publish /tmp/symptomcalm-article.html'.
If the article's pillar page exists, update its CTA section to link to the new article.
Verify the page is live with curl.
" --skills tcm-content-production 2>&1 >> "$HOME/symptomcalm/.cron/publish.log"

echo "$(date): Auto-publish run complete" >> "$HOME/symptomcalm/.cron/publish.log"
