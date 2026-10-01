#!/usr/bin/env python3
"""Report missing ZH pages without generating thin placeholder content."""
import os
import subprocess

WORK = os.path.expanduser("~/symptomcalm")
result = subprocess.run(
    ['find', 'symptoms', 'tcm-basics', 'treatments', '-mindepth', '2', '-maxdepth', '3', '-name', 'index.html'],
    capture_output=True, text=True, cwd=WORK, timeout=30
)
missing = []
for p in result.stdout.strip().split('\n'):
    p = p.strip()
    if not p:
        continue
    zh_file = f"zh/{os.path.dirname(p)}/index.html"
    if not os.path.exists(os.path.join(WORK, zh_file)):
        missing.append((p, zh_file))

print(f"Found {len(missing)} missing ZH files")
for en_rel, zh_rel in missing:
    print(f"MISSING_TRANSLATION {en_rel} -> {zh_rel}")
if missing:
    print("No placeholder pages generated; complete these translations manually before publishing.")
else:
    print("All English article pages have ZH mirrors.")