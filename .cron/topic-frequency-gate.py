#!/usr/bin/env python3
"""Select an eligible queue item and enforce topic-cluster pacing.

Only items published with published_at are counted; legacy queue history has no
reliable timestamps and is intentionally not retroactively guessed.
"""
import json, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / ".content-queue.json"
LIMIT = 3
WINDOW = timedelta(days=30)

def main():
    data = json.loads(QUEUE.read_text())
    now = datetime.now(timezone.utc)
    recent = []
    for item in data.get("published", []):
        stamp = item.get("published_at")
        if not stamp:
            continue
        try:
            if now - datetime.fromisoformat(stamp.replace("Z", "+00:00")) <= WINDOW:
                recent.append(item)
        except ValueError:
            continue
    counts = {}
    for item in recent:
        parent = item.get("parent") or "uncategorized"
        counts[parent] = counts.get(parent, 0) + 1
    queue = data.get("queue", [])
    if not queue:
        print("TOPIC_GATE_EMPTY")
        return 1
    eligible = next((i for i in queue if counts.get(i.get("parent") or "uncategorized", 0) < LIMIT), None)
    if eligible is None:
        print("TOPIC_GATE_BLOCKED all queue clusters reached 30-day limit", file=sys.stderr)
        return 1
    if eligible is not queue[0]:
        queue.remove(eligible)
        queue.insert(0, eligible)
        QUEUE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        print(f"TOPIC_GATE_ROTATED parent={eligible.get('parent')} title={eligible.get('title')}")
    print(f"TOPIC_GATE_OK parent={eligible.get('parent')} recent={counts.get(eligible.get('parent'), 0)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
