#!/usr/bin/env python3
"""
Post-publish content quality verification for SymptomCalm.
Run after publish-article.py publish <article.html> to verify quality.

Covers both structural checks (disclaimer, word count, sections) and
SEO meta consistency (meta desc length, OG/title sync, forbidden words).

Usage:
  python3 scripts/content-quality-check.py <path-to-article-index.html>

Returns exit code 0 if all checks pass, 1 on warnings, 2 on failures.
"""

import re
import sys
import json
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("Usage: content-quality-check.py <path-to-index.html>")
        sys.exit(2)

    html_path = Path(sys.argv[1])
    if not html_path.exists():
        print(f"❌ FAIL: File not found: {html_path}")
        sys.exit(2)

    html = html_path.read_text()
    site_root = Path.cwd()
    results = {"pass": 0, "warn": 0, "fail": 0, "checks": []}
    critical_fail = False

    # 1. File size
    size = len(html.encode("utf-8"))
    if size >= 1000:
        results["pass"] += 1
        results["checks"].append(f"✅ File size: {size:,} bytes (≥1KB)")
    else:
        critical_fail = True
        results["fail"] += 1
        results["checks"].append(f"❌ File size: {size:,} bytes (<1KB!)")

    # 2. Word count (article body only)
    body_match = re.search(r'<div class="article-body">(.*?)</article>', html, re.DOTALL)
    if body_match:
        body = re.sub(r'<[^>]+>', " ", body_match.group(1))
        body = re.sub(r'\s+', " ", body).strip()
        wc = len(body.split())
        if wc >= 800:
            results["pass"] += 1
        else:
            results["warn"] += 1
        results["checks"].append(
            f"{'✅' if wc >= 800 else '⚠️'} Word count: ~{wc} "
            f"({'≥800' if wc >= 800 else '<800!'})"
        )
    else:
        results["fail"] += 1
        results["checks"].append("❌ FAIL: Could not extract article body")

    # 3. Disclaimer banner
    if "disclaimer-banner" in html:
        results["pass"] += 1
        results["checks"].append("✅ Disclaimer banner present")
    else:
        results["warn"] += 1
        results["checks"].append("⚠️ WARN: No disclaimer-banner found")

    # 4. When to See a Doctor
    if "When to See a Doctor" in html:
        results["pass"] += 1
        results["checks"].append("✅ 'When to See a Doctor' section present")
    else:
        results["warn"] += 1
        results["checks"].append("⚠️ WARN: Missing 'When to See a Doctor' section")

    # 5. Research / scientific reference section
    research_signals = [
        "Research", "studies suggest", "studies show",
        "research suggests", "Modern science", "scientific",
    ]
    matched_research = [s for s in research_signals if s in html]
    if matched_research:
        results["pass"] += 1
        results["checks"].append(f"✅ Research/scientific references present (matched: {', '.join(matched_research[:2])})")
    else:
        results["warn"] += 1
        results["checks"].append("⚠️ WARN: No research or scientific reference found")

    # 6. Practical Takeaways / actionable advice section
    practical_signals = [
        "Practical Takeaways", "Practical Tips", "Practical Ways",
        "How to Support", "What You Can Do", "Actionable",
    ]
    if any(sig in html for sig in practical_signals):
        results["pass"] += 1
        results["checks"].append("✅ Practical advice section present")
    else:
        results["warn"] += 1
        results["checks"].append("⚠️ WARN: Missing practical advice section")

    # 7. Meta description length ≤ 160 chars
    meta_desc_match = re.search(r'<meta name="description" content="([^"]+)"', html)
    if meta_desc_match:
        md_len = len(meta_desc_match.group(1))
        if md_len <= 160:
            results["pass"] += 1
            results["checks"].append(f"✅ Meta description length: {md_len} chars (≤160)")
        else:
            results["warn"] += 1
            results["checks"].append(f"⚠️ WARN: Meta description too long: {md_len} chars (>160)")
    else:
        results["fail"] += 1
        results["checks"].append("❌ FAIL: No meta description found")

    # 8. OG description matches meta description
    og_desc_match = re.search(r'<meta property="og:description" content="([^"]+)"', html)
    if meta_desc_match and og_desc_match:
        if og_desc_match.group(1) == meta_desc_match.group(1):
            results["pass"] += 1
            results["checks"].append("✅ OG description matches meta description")
        else:
            results["warn"] += 1
            results["checks"].append("⚠️ WARN: OG description differs from meta description")

    # 9. Title matches OG title (both must have "— SymptomCalm" suffix)
    title_match = re.search(r'<title>([^<]+)</title>', html)
    og_title_match = re.search(r'<meta property="og:title" content="([^"]+)"', html)
    if title_match and og_title_match:
        if title_match.group(1) == og_title_match.group(1):
            results["pass"] += 1
            if "— SymptomCalm" in title_match.group(1):
                results["checks"].append("✅ Title == OG title with '— SymptomCalm' suffix")
            else:
                results["warn"] += 1
                results["checks"].append("⚠️ WARN: Title/OG title match but missing '— SymptomCalm' suffix")
        else:
            results["warn"] += 1
            results["checks"].append("⚠️ WARN: Title differs from OG title")

    # 10. Forbidden words scan with safe-context filtering
    if body_match:
        forbidden = [
            (r'\bcure\b', "cure"),
            (r'\btreat\b', "treat"),
            (r'\bheal\b', "heal"),
        ]
        body_lower = body_match.group(1).lower()
        found = []
        for pattern, word in forbidden:
            matches = re.findall(pattern, body_lower)
            if matches:
                unsafe = 0
                for m in re.finditer(pattern, body_lower):
                    start = max(0, m.start() - 40)
                    end = min(len(body_lower), m.end() + 40)
                    ctx = body_lower[start:end]
                    # Safe context detection
                    safe = False
                    if word == "heal" and ("health" in ctx or "healthcare" in ctx):
                        safe = True
                    if word == "treat":
                        if "treats " in ctx and (" as " in ctx or " like " in ctx):
                            safe = True  # "treats X as Y" = considers, not medical
                    if not safe:
                        unsafe += 1
                if unsafe > 0:
                    found.append(f"{word}(x{unsafe} unsafe)")
        if found:
            results["warn"] += 1
            results["checks"].append(f"⚠️ WARN: Forbidden words found: {', '.join(found)} (review context)")
        else:
            results["pass"] += 1
            results["checks"].append("✅ No forbidden treatment words in body")

    # 11. Queue integrity check (optional, if in site root)
    queue_path = site_root / ".content-queue.json"
    if queue_path.exists():
        try:
            data = json.loads(queue_path.read_text())
            pub_paths = {p["path"] for p in data["published"]}
            queue_dup = 0
            for item in data["queue"]:
                if item["path"] in pub_paths:
                    queue_dup += 1
            if queue_dup:
                results["warn"] += 1
                results["checks"].append(f"⚠️ WARN: {queue_dup} duplicate path(s) in queue")
            else:
                results["pass"] += 1
                results["checks"].append(f"✅ Queue OK: {len(data['queue'])} remaining, {len(data['published'])} published")
        except (json.JSONDecodeError, KeyError) as e:
            results["warn"] += 1
            results["checks"].append(f"⚠️ WARN: Queue file parse error: {e}")

    # Summary
    print(f"\n{'='*50}")
    print(f"CONTENT QUALITY VERIFICATION")
    print(f"{'='*50}")
    print(f"File: {html_path}")
    for check in results["checks"]:
        print(f"  {check}")
    print(f"{'='*50}")
    print(f"Passed: {results['pass']}  Warnings: {results['warn']}  Failed: {results['fail']}")
    print(f"{'='*50}\n")

    sys.exit(2 if critical_fail else (1 if results["warn"] or results["fail"] else 0))


if __name__ == "__main__":
    main()
