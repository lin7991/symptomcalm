#!/bin/bash
# SymptomCalm auto-publisher — fired by launchd every 3 hours
# Generates EN + ZH article, publishes, then FAQ schema

export HERMES_HOME="$HOME/.hermes"
export PATH="/usr/local/bin:/opt/homebrew/bin:$HOME/.local/bin:$PATH"

cd "$HOME/symptomcalm" || exit 1

REMAINING=$(python3 .cron/publish-article.py remaining 2>/dev/null)
echo "$(date): Queue has $REMAINING items" >> "$HOME/symptomcalm/.cron/publish.log"

# Run Hermes to publish EN + ZH
hermes chat --profile symptomcalm -Q -q "
You are in ~/symptomcalm.

STEP 1: Check queue. If remaining < 5, generate 15 new ideas and pipe to add command.

STEP 2: Publish ENGLISH article.
- Read next item from queue
- Use .cron/article-template.html
- Replace <!--NEWSLETTER_SECTION--> with actual newsletter form HTML
- Replace <!--FAQ_SCHEMA--> with empty string
- Write to /tmp/sc-en.html
- Run: python3 .cron/publish-article.py publish /tmp/sc-en.html
- If pillar page exists, update its CTA to link to new article

STEP 3: Publish CHINESE version.
- Read same English article from /tmp/sc-en.html to get title/info
- Use .cron/article-template-zh.html
- Replace <!--NEWSLETTER_SECTION--> with Chinese version form HTML
- Replace <!--FAQ_SCHEMA_ZH--> with empty string
- Write to /tmp/sc-zh.html
- Determine path from queue item, create directory: mkdir -p zh/CURRENT_PATH
- Copy: cp /tmp/sc-zh.html zh/CURRENT_PATH/index.html
- Git add and commit

STEP 4: Verify both EN and ZH pages with curl.
" --skills tcm-content-production 2>&1 >> "$HOME/symptomcalm/.cron/publish.log"

echo "$(date): Auto-publish EN+ZH complete" >> "$HOME/symptomcalm/.cron/publish.log"

# Generate FAQ schema
echo "$(date): Generating FAQ schema..." >> "$HOME/symptomcalm/.cron/publish.log"
python3 .cron/add-faq-schema.py >> "$HOME/symptomcalm/.cron/publish.log" 2>&1

# Commit all changes
cd "$HOME/symptomcalm"
git add -A 2>/dev/null
git diff --cached --quiet || git commit -m "Auto publish EN+ZH + FAQ" && git push origin main 2>/dev/null

echo "$(date): Auto-publish cycle finished" >> "$HOME/symptomcalm/.cron/publish.log"
