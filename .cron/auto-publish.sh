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

|STEP 2: Read next item with 'python3 .cron/publish-article.py next'.
|Generate a complete HTML article using .cron/article-template.html.
|The template has a <!--NEWSLETTER_SECTION--> placeholder — replace it with:
|<section class=\"newsletter-section\"><div class=\"container\"><div class=\"newsletter-box\">
|<h3>Stay in the Loop</h3><p>Get weekly TCM insights delivered to your inbox.</p>
|<form id=\"newsletter-form\" style=\"display:contents\">
|<input type=\"email\" id=\"newsletter-email\" placeholder=\"Your email address\" required />
|<button type=\"submit\">Subscribe</button>
|</form><p id=\"newsletter-message\"></p></div></div></section>
|The template also has <!--FAQ_SCHEMA--> — leave it as is (FAQ script handles it after publish).
|Write the final HTML to /tmp/symptomcalm-article.html.
|Run 'python3 .cron/publish-article.py publish /tmp/symptomcalm-article.html'.
If the article's pillar page exists, update its CTA section to link to the new article.
Verify the page is live with curl.
" --skills tcm-content-production 2>&1 >> "$HOME/symptomcalm/.cron/publish.log"

echo "$(date): Auto-publish run complete" >> "$HOME/symptomcalm/.cron/publish.log"

# Step 3: Generate FAQ schema for the new article
echo "$(date): Generating FAQ schema..." >> "$HOME/symptomcalm/.cron/publish.log"
python3 .cron/add-faq-schema.py >> "$HOME/symptomcalm/.cron/publish.log" 2>&1

# Commit FAQ schema changes
cd "$HOME/symptomcalm"
git add -A 2>/dev/null
git diff --cached --quiet || git commit -m "Auto FAQ schema update" && git push origin main 2>/dev/null

echo "$(date): Auto-publish cycle finished" >> "$HOME/symptomcalm/.cron/publish.log"
