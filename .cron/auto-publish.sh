#!/bin/bash
# SymptomCalm auto-publisher — fired twice daily at 00:05 and 06:05
# Generates EN + ZH articles, publishes, then runs deterministic SEO post-processing.

export HERMES_HOME="$HOME/.hermes"
export PATH="/usr/local/bin:/opt/homebrew/bin:$HOME/.local/bin:$PATH"

export AUTO_PUBLISH_BATCH=1

# --- git auth hardening (launchd has no GUI/keychain session) ---
# Without these, `git push` blocks forever waiting for a username prompt.
# (This hung the pipeline for 6 days, Sep 15-21 2026.)
ASKPASS="$HOME/.hermes/profiles/symptomcalm/.git-askpass.sh"
[ -x "$ASKPASS" ] && export GIT_ASKPASS="$ASKPASS"
export GIT_TERMINAL_PROMPT=0
export GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=10"
# --- end git auth hardening ---


cd "$HOME/symptomcalm" || exit 1

# Production publishing must run from the branch that is intentionally deployed.
# A detached/feature branch must never push a stale local `main` ref.
BRANCH=$(git branch --show-current 2>/dev/null)
if [ "$BRANCH" != "main" ]; then
  echo "$(date): WRONG BRANCH ($BRANCH) — refusing production publish" >> "$HOME/symptomcalm/.cron/publish.log"
  exit 1
fi

# Single-writer + clean-worktree guard. The old pipeline shared /tmp/sc-*.html
# and ran git add -A; concurrent/dirty runs could publish one article at another
# URL and commit unrelated work. Never start a publish cycle in either state.
LOCKDIR="$HOME/symptomcalm/.cron/.auto-publish.lock"
if ! mkdir "$LOCKDIR" 2>/dev/null; then
  echo "$(date): another auto-publish cycle is running; aborting" >> "$HOME/symptomcalm/.cron/publish.log"
  exit 0
fi
RUN_DIR=$(mktemp -d "$HOME/symptomcalm/.cron/run.XXXXXX") || exit 1
BASE_SHA=$(git rev-parse HEAD)
rollback_run() {
  git reset --hard "$BASE_SHA" >/dev/null 2>&1 || true
  # Remove only publisher-owned untracked artifacts; preserve logs and any
  # pre-existing user files even if a future guard is accidentally bypassed.
  find .cron -maxdepth 1 -type d -name 'run.*' -exec rm -rf {} + 2>/dev/null || true
  find .cron -maxdepth 1 -type f -name 'generate_*.py' -delete 2>/dev/null || true
}
trap 'rmdir "$LOCKDIR" 2>/dev/null || true; rm -rf "$RUN_DIR" 2>/dev/null || true' EXIT INT TERM
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
  echo "$(date): DIRTY WORKTREE — refusing to publish or git add -A" >> "$HOME/symptomcalm/.cron/publish.log"
  git status --short >> "$HOME/symptomcalm/.cron/publish.log"
  exit 1
fi

REMAINING=$(python3 .cron/publish-article.py remaining 2>/dev/null)
echo "$(date): Queue has $REMAINING items" >> "$HOME/symptomcalm/.cron/publish.log"
QUEUE_BEFORE="$REMAINING"

# Run Hermes to publish 2 articles (EN + ZH each)
if ! hermes chat --profile symptomcalm -Q -q "
You are in ~/symptomcalm.

STEP 1: Check queue. If remaining < 5, generate 15 new ideas and pipe to add command.

STEP 2: Publish TWO articles in this run. For EACH of the next 2 queue items, do:
A) ENGLISH article:
- Read next item from queue
- Use .cron/article-template.html
- Replace <!--NEWSLETTER_SECTION--> with empty string
- Replace <!--FAQ_SCHEMA--> with empty string
- Write to $RUN_DIR/sc-en.html
- Run: python3 .cron/publish-article.py publish $RUN_DIR/sc-en.html
- If pillar page exists, update its CTA to link to new article

B) CHINESE version:
- Read the same English article from $RUN_DIR/sc-en.html to get title/info
- Use .cron/article-template-zh.html
- Replace <!--NEWSLETTER_SECTION--> with empty string
- Replace <!--FAQ_SCHEMA_ZH--> with empty string
- Write to $RUN_DIR/sc-zh.html
- Determine path from queue item, create directory: mkdir -p zh/CURRENT_PATH
- Copy: cp $RUN_DIR/sc-zh.html zh/CURRENT_PATH/index.html
- Do NOT run git add, git commit, git push, reset, checkout, or clean. The outer shell script owns Git and will reject a dirty/failed release.

Repeat A+B for the second article.

STEP 3: Verify both EN and ZH pages with curl.
" --skills tcm-content-production >> "$HOME/symptomcalm/.cron/publish.log" 2>&1; then
  echo "$(date): HERMES GENERATION FAILED — rolling back cycle" >> "$HOME/symptomcalm/.cron/publish.log"
  rollback_run
  exit 1
fi

echo "$(date): Auto-publish 2x EN+ZH complete" >> "$HOME/symptomcalm/.cron/publish.log"

# Guard: a failed model/API call makes the generator exit without publishing,
# yet the cycle used to keep going and commit metadata-only noise. Worse, a
# broken key looked like a healthy run. Refuse to continue unless the queue
# actually shrank.
QUEUE_AFTER=$(python3 .cron/publish-article.py remaining 2>/dev/null)
if [ -n "$QUEUE_BEFORE" ] && [ -n "$QUEUE_AFTER" ] && [ "$QUEUE_AFTER" -ge "$QUEUE_BEFORE" ]; then
  echo "$(date): CONTENT GENERATION FAILED — queue $QUEUE_BEFORE -> $QUEUE_AFTER, no article produced. Rolling back cycle." >> "$HOME/symptomcalm/.cron/publish.log"
  rollback_run
  exit 1
fi
echo "$(date): Queue $QUEUE_BEFORE -> $QUEUE_AFTER (published)" >> "$HOME/symptomcalm/.cron/publish.log"

# Regenerate RSS feed
echo "$(date): Regenerating RSS feed..." >> "$HOME/symptomcalm/.cron/publish.log"
python3 .cron/gen-rss.py >> "$HOME/symptomcalm/.cron/publish.log" 2>&1

# Update share buttons + og:image for new pages
echo "$(date): Updating share/images..." >> "$HOME/symptomcalm/.cron/publish.log"
python3 .cron/add-share-images.py >> "$HOME/symptomcalm/.cron/publish.log" 2>&1

# Add Breadcrumb + Article schema to new pages
echo "$(date): Adding schemas..." >> "$HOME/symptomcalm/.cron/publish.log"
python3 .cron/add-schemas.py >> "$HOME/symptomcalm/.cron/publish.log" 2>&1

# Add hreflang bidirectional tags
echo "$(date): Adding hreflang..." >> "$HOME/symptomcalm/.cron/publish.log"
python3 .cron/add-hreflang.py >> "$HOME/symptomcalm/.cron/publish.log" 2>&1

# Refresh canonical, hreflang, entity schema and GEO metadata LAST among metadata
# writers: it rewrites the whole ld+json graph, so anything that adds its own
# block (add-schemas.py) must already have run or its output gets dropped.
python3 .cron/refresh-seo-geo.py >> "$HOME/symptomcalm/.cron/publish.log" 2>&1

# Generate FAQ schema last of all: refresh-seo-geo.py strips every ld+json block.
echo "$(date): Generating FAQ schema last..." >> "$HOME/symptomcalm/.cron/publish.log"
python3 .cron/add-faq-schema.py >> "$HOME/symptomcalm/.cron/publish.log" 2>&1

# Ensure ZH mirror exists for new articles (batch fallback)
echo "$(date): Ensuring ZH mirrors..." >> "$HOME/symptomcalm/.cron/publish.log"
python3 .cron/batch-zh.py >> "$HOME/symptomcalm/.cron/publish.log" 2>&1

# Rebuild sitemap from the actual filesystem after all page writes
python3 .cron/rebuild-sitemap.py >> "$HOME/symptomcalm/.cron/publish.log" 2>&1

# Release gate: block the commit if required content/SEO fields are missing
if ! python3 .cron/content-quality-gate.py >> "$HOME/symptomcalm/.cron/publish.log" 2>&1; then
  echo "$(date): QUALITY GATE FAILED — refusing to commit; rolling back cycle" >> "$HOME/symptomcalm/.cron/publish.log"
  rollback_run
  exit 1
fi

# Final full-site SEO/GEO release gate. This catches identity drift, same-language
# duplicate bodies, sitemap pollution, and malformed metadata before any commit.
echo "$(date): Running final SEO/GEO release gate..." >> "$HOME/symptomcalm/.cron/publish.log"
if ! python3 .cron/weekly-seo-geo-audit.py >> "$HOME/symptomcalm/.cron/publish.log" 2>&1; then
  echo "$(date): SEO/GEO RELEASE GATE FAILED — refusing to commit; rolling back cycle" >> "$HOME/symptomcalm/.cron/publish.log"
  rollback_run
  exit 1
fi

# Commit all changes
cd "$HOME/symptomcalm"
LOG="$HOME/symptomcalm/.cron/publish.log"
# Stage only publisher outputs. Do not use git add -A: logs, reports, and
# unrelated user files must never enter a production commit.
git add .content-queue.json sitemap.xml rss.xml 2>/dev/null || true
while IFS= read -r changed; do
  case "$changed" in
    *.html) git add -- "$changed" ;;
  esac
done < <(git status --porcelain=v1 | sed -E 's/^.. //; s/^"//; s/"$//')
if ! git diff --cached --quiet 2>/dev/null; then
  git commit -m "Auto publish EN+ZH + FAQ" >> "$LOG" 2>&1
  # Bounded push: no credential prompt (GIT_ASKPASS above), abort on slow/stalled link.
  PUSH_ARGS="-c credential.helper= -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=20"
  if git $PUSH_ARGS push origin main >> "$LOG" 2>&1; then
    echo "$(date): push OK" >> "$LOG"
  else
    echo "$(date): git push failed — trying chunked GitHub API fallback" >> "$LOG"
    # Chunked tree build: a single /git/trees POST with 1000+ entries returns
    # "Server Error" (verified twice: 1995-file GEO push, 1987-file auto-publish run).
    python3 "$HOME/symptomcalm/scripts/api_push_chunked.py" --apply --batch 100 \
      --msg "auto-publish $(date +%F)" >> "$LOG" 2>&1 || \
      echo "$(date): API push fallback also failed" >> "$LOG"
  fi
fi

echo "$(date): Auto-publish cycle finished" >> "$LOG"
