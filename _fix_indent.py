#!/usr/bin/env python3
"""Fix the lang-toggle button indentation and clean up."""
import os
import re

BASE = "/Users/xj/symptomcalm"
EXCLUDE_DIRS = {".git", "node_modules", ".cron"}

def find_html_files():
    files = []
    for root, dirs, fnames in os.walk(BASE):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in fnames:
            if f.endswith(".html"):
                files.append(os.path.join(root, f))
    return sorted(files)

def fix_indentation(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    original = content
    
    # Fix: replace 10-space indentation on the lang-toggle button with 6 spaces
    content = content.replace(
        '          <button id="lang-toggle" class="lang-toggle">',
        '      <button id="lang-toggle" class="lang-toggle">'
    )
    
    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False

def check_cron_files():
    cron_dir = os.path.join(BASE, ".cron")
    if not os.path.isdir(cron_dir):
        return
    for f in os.listdir(cron_dir):
        if f.endswith(".html"):
            fp = os.path.join(cron_dir, f)
            with open(fp, "r", encoding="utf-8") as fh:
                c = fh.read()
            if "lang-toggle" in c:
                print(f"  NOTE: {fp} has lang-toggle (was processed despite exclusion)")
            if "newsletter-section" in c:
                print(f"  NOTE: {fp} has newsletter-section (was processed despite exclusion)")

files = find_html_files()
fix_count = 0
for f in files:
    if fix_indentation(f):
        fix_count += 1

print(f"Fixed indentation in {fix_count} files")

check_cron_files()

# Remove the batch script
script_path = os.path.join(BASE, "_batch_update.py")
if os.path.exists(script_path):
    os.remove(script_path)
    print("Cleaned up _batch_update.py")
