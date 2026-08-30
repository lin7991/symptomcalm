#!/usr/bin/env python3
"""
Post-publish URL verification for SymptomCalm.
Checks whether a published article is live on the site,
diagnoses Cloudflare cache issues, and confirms git remote status.

Usage:
  python3 scripts/verify-publish.py <article-path>
  python3 scripts/verify-publish.py /tcm-basics/spleen-qi-sinking/

Diagnoses:
  - raw.githubusercontent.com: definitive remote presence check
  - Cloudflare cache age: distinguishes fresh vs cached 404
  - git branch tracking: confirms remote has the commit
  - Existing article comparison: rules out global deployment failure
"""

import subprocess
import sys
import urllib.request
import re
from pathlib import Path


def curl_status(url, extra_headers=None):
    """Return HTTP status code for a URL."""
    req = urllib.request.Request(url, method="HEAD")
    if extra_headers:
        for k, v in extra_headers.items():
            req.add_header(k, v)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return resp.status, dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers)
    except Exception as e:
        return 0, {"error": str(e)}


def main():
    if len(sys.argv) < 2:
        print("Usage: verify-publish.py <article-path>")
        print("  e.g. verify-publish.py /tcm-basics/spleen-qi-sinking/")
        sys.exit(1)

    art_path = sys.argv[1].rstrip("/")
    site_root = Path.cwd()

    print(f"{'='*55}")
    print(f"  PUBLISH VERIFICATION: {art_path}/")
    print(f"{'='*55}")

    results = []
    all_pass = True

    # --- Check 1: File exists on local disk ---
    file_path = site_root / art_path.lstrip("/") / "index.html"
    if file_path.exists():
        size = len(file_path.read_bytes())
        results.append(f"  [{'OK' if size > 100 else 'BAD'}] File on disk: {file_path} ({size:,} bytes)")
        if size <= 100:
            all_pass = False
    else:
        results.append(f"  [MISSING] File not found: {file_path}")
        all_pass = False

    # --- Check 2: Raw file on GitHub (definitive remote check) ---
    raw_url = f"https://raw.githubusercontent.com/lin7991/symptomcalm/main{art_path}/index.html"
    status, headers = curl_status(raw_url)
    if status == 200:
        results.append(f"  [OK] Raw on GitHub: {raw_url}")
    else:
        results.append(f"  [FAIL] Raw on GitHub returned {status} — article never reached remote")
        all_pass = False

    # --- Check 3: Git remote tracking ---
    try:
        result = subprocess.run(
            ["git", "branch", "-vv"],
            capture_output=True, text=True, timeout=10
        )
        branch_info = result.stdout.strip()
        if "[origin/main" in branch_info:
            # Extract the commit message
            m = re.search(r"\* main\s+(\S+)\s+\[origin/main[^\]]*\]\s+(.+)", branch_info)
            if m:
                results.append(f"  [OK] Git tracking: {m.group(1)} \"{m.group(2)[:60]}\"")
            else:
                results.append(f"  [OK] Git tracking origin/main")
        elif "ahead" in branch_info:
            results.append(f"  [AHEAD] Local has unpushed commits — run git push")
            all_pass = False
        else:
            results.append(f"  [WARN] Git tracking status unclear: {branch_info[:80]}")
    except Exception as e:
        results.append(f"  [WARN] Could not check git status: {e}")

    # --- Check 4: Cloudflare site URL ---
    site_url = f"https://symptomcalm.com{art_path}/"
    status, headers = curl_status(site_url)
    age = headers.get("age", "?")
    x_cache = headers.get("x-cache", "?")
    cf_cache = headers.get("cf-cache-status", "?")
    x_proxy = headers.get("x-proxy-cache", "?")

    if status == 200:
        results.append(f"  [OK] Site URL: {site_url}")
    elif status == 404:
        if x_cache == "HIT" and age not in ("?", "0"):
            results.append(f"  [CACHED] 404 via Cloudflare (age={age}s, x-cache={x_cache}) — waiting for cache to expire")
            results.append(f"    Try: sleep 120 && curl -sI {site_url}")
        else:
            results.append(f"  [404] Site URL returned {status} (age={age}s, x-cache={x_cache})")
            all_pass = False
    else:
        results.append(f"  [WARN] Site URL returned {status}")

    # --- Check 5: Existing article comparison (if new URL is 404) ---
    if status != 200:
        existing_path = "/tcm-basics/what-is-qi/"
        ref_status, _ = curl_status(f"https://symptomcalm.com{existing_path}")
        results.append(f"  [{'OK' if ref_status == 200 else 'WARN'}] Existing page {existing_path}: {ref_status}")
        if ref_status != 200:
            results.append(f"    ⚠️  Existing page also broken — possible global deployment failure!")

    # --- Summary ---
    print(f"{'-'*55}")
    for r in results:
        print(r)
    print(f"{'-'*55}")
    print(f"  Verdict: {'ALL CHECKS PASSED' if all_pass else 'ISSUES FOUND (see above)'}")
    print(f"{'='*55}")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
