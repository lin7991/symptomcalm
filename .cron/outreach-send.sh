#!/bin/bash
# SymptomCalm Link Outreach — fired by launchd every hour
PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$HOME/.local/bin"
cd "$HOME/symptomcalm" || exit 1

# Try to find emails and send the next one
python3 .cron/outreach.py send 2>&1 >> "$HOME/symptomcalm/.cron/outreach/send.log"
echo "$(date): outreach run complete" >> "$HOME/symptomcalm/.cron/outreach/send.log"
