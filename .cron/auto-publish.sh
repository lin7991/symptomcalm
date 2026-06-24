#!/bin/bash
# SymptomCalm auto-publisher — fired by launchd every 3 hours
# Uses hermes chat in one-shot mode to generate and publish content

export HERMES_HOME="$HOME/.hermes"
export PATH="/usr/local/bin:/opt/homebrew/bin:$HOME/.local/bin:$PATH"

cd "$HOME/symptomcalm" || exit 1

# Check if we have a next article
NEXT=$(python3 .cron/publish-article.py remaining 2>/dev/null)
if [ "$NEXT" = "0" ] || [ -z "$NEXT" ]; then
  echo "Queue empty, nothing to publish"
  exit 0
fi

# Run Hermes in one-shot to generate and publish the next article
# Timeout after 15 minutes to prevent hanging
hermes chat --profile symptomcalm -Q -q "
You are in ~/symptomcalm. Read the queue with 'python3 .cron/publish-article.py next'.
Generate a complete HTML article for that item using the template at .cron/article-template.html.
Write the HTML to /tmp/symptomcalm-article.html.
Then run 'python3 .cron/publish-article.py publish /tmp/symptomcalm-article.html'.
If the article is yin-yang-explained or how-acupuncture-works, also update index.html to 
replace 'Coming soon' with a real link.
Then verify the page is live: curl -sI 'https://symptomcalm.com/...'
Finally run: python3 .cron/publish-article.py status
" --skills tcm-content-production 2>&1 >> "$HOME/symptomcalm/.cron/publish.log"

echo "$(date): Auto-publish run complete" >> "$HOME/symptomcalm/.cron/publish.log"
