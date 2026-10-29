#!/usr/bin/env python3
"""
SymptomCalm Auto-Publisher — mechanical helper for the 3-hour cron job.

Usage:
    python3 publish-article.py next          # Print the next article info
    python3 publish-article.py publish <html_content_file>
                                             # Create the article HTML, update sitemap, git push
                                             # Reads HTML content from the specified file

Environment:
    WORKDIR: defaults to ~/symptomcalm (or set explicitly)
"""

import json, os, re, shutil, subprocess, sys, time, html
from pathlib import Path

WORKDIR = Path(os.environ.get("WORKDIR", os.path.expanduser("~/symptomcalm")))
QUEUE_FILE = WORKDIR / ".content-queue.json"
SITEMAP_FILE = WORKDIR / "sitemap.xml"
ARTICLE_TEMPLATE = (WORKDIR / ".cron").resolve() / "article-template.html"


def load_queue():
    with open(QUEUE_FILE) as f:
        return json.load(f)


def save_queue(data):
    with open(QUEUE_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def get_next():
    data = load_queue()
    if not data["queue"]:
        return None
    return data["queue"][0]


def queue_remaining():
    """Return number of items still in the queue."""
    data = load_queue()
    return len(data["queue"])


def add_to_queue(new_items):
    """Append new items to the queue (list of dicts)."""
    data = load_queue()
    max_id = max((int(item["id"]) for item in data["queue"] + data["published"]), default=0)
    for item in new_items:
        max_id += 1
        item["id"] = f"{max_id:02d}"
    data["queue"].extend(new_items)
    save_queue(data)
    print(f"Added {len(new_items)} items to queue. Total remaining: {len(data['queue'])}")


def _gitenv():
    """Env for git: never prompt (launchd/cron has no keychain session)."""
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    ask = os.path.expanduser("~/.hermes/profiles/symptomcalm/.git-askpass.sh")
    if os.path.exists(ask):
        env["GIT_ASKPASS"] = ask
    return env


_GIT = ["git", "-c", "credential.helper=",
        "-c", "http.lowSpeedLimit=1000", "-c", "http.lowSpeedTime=20"]


def _git(args, timeout=90):
    """Run git with a hard timeout so a stalled link can never wedge the cron."""
    try:
        return subprocess.run(_GIT + args, capture_output=True, text=True,
                              cwd=str(WORKDIR), env=_gitenv(), timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"WARNING: git {' '.join(args)} timed out after {timeout}s", file=sys.stderr)
        return subprocess.CompletedProcess(_GIT + args, 124, "", "timeout")


def commit_and_push(article_path):
    """Git commit and push the new article (bounded, non-interactive, API fallback)."""
    article_id = article_path.relative_to(WORKDIR)
    commit_msg = f"Auto-publish: {article_id}"

    _git(["add", str(article_path), str(SITEMAP_FILE), str(QUEUE_FILE)])
    result = _git(["commit", "-m", commit_msg])
    if result.returncode != 0 and "nothing to commit" not in (result.stderr or ""):
        print(f"Commit warning: {result.stderr}", file=sys.stderr)

    result = _git(["push", "origin", "main"])
    if result.returncode != 0:
        # Remote moved (or link unavailable): integrate then retry once.
        # merge (not rebase) — safer with several unpushed commits, one conflict pass.
        _git(["fetch", "origin", "main"], timeout=90)
        _git(["rebase", "--abort"], timeout=30)      # clear any leftover rebase state
        merged = _git(["merge", "--no-commit", "--no-edit", "origin/main"])
        if merged.returncode != 0:
            _git(["merge", "--abort"], timeout=30)
        result = _git(["push", "origin", "main"])
    if result.returncode != 0:
        # github.com:443 is frequently unreachable here; push via the Git Data API.
        try:
            # api_push.py posts ONE tree with every candidate -> GitHub 422s once the
            # backlog passes ~500 files. Prefer the chunked variant (chained base_tree
            # batches) when present.
            chunked = WORKDIR / "scripts" / "api_push_chunked.py"
            if chunked.exists():
                cmd = [sys.executable, str(chunked), "--apply", "--batch", "100"]
            else:
                cmd = [sys.executable, str(WORKDIR / "scripts" / "api_push.py"), "--apply"]
            api = subprocess.run(cmd, capture_output=True, text=True, timeout=1500)
            tail = (api.stdout or "")[-300:]
            print("API push fallback:", tail)
            out = api.stdout or ""
            return "ALL MATCH: True" in out or "PUSHED ITEMS MATCH: True" in out
        except Exception as exc:                     # noqa: BLE001
            print(f"API push fallback failed: {exc}", file=sys.stderr)
            return False
    return True



def update_sitemap(article_path):
    """Add the new article URL to sitemap.xml (handles both plain and ns0:-namespaced formats)."""
    url = f"https://symptomcalm.com{article_path}/"
    with open(SITEMAP_FILE) as f:
        content = f.read()

    if url in content:
        print(f"Sitemap unchanged: {url} already exists")
        return

    # Plain sitemap format: insert before </urlset>
    insert = f"""  <url>
    <loc>{url}</loc>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>"""
    if "</urlset>" in content:
        content = content.replace("</urlset>", f"{insert}\n</urlset>")
    else:
        # Namespaced format (ns0: prefix): build the entry with the same prefix.
        m = re.search(r"</(ns\d+):urlset>", content)
        if m:
            prefix = m.group(1)
            insert_ns = f"""  <{prefix}:url>
    <{prefix}:loc>{url}</{prefix}:loc>
    <{prefix}:changefreq>monthly</{prefix}:changefreq>
    <{prefix}:priority>0.7</{prefix}:priority>
  </{prefix}:url>"""
            content = content.replace(f"</{prefix}:urlset>", f"{insert_ns}\n</{prefix}:urlset>")
        else:
            print(f"WARNING: could not find urlset close tag in {SITEMAP_FILE}", file=sys.stderr)
            return
    with open(SITEMAP_FILE, "w") as f:
        f.write(content)
    print(f"Sitemap updated: {url}")


def ensure_release_metadata(html_content: str, article_path: str) -> str:
    """Add deterministic SEO/GEO metadata before a generated page is written."""
    url = "https://symptomcalm.com/" + article_path.strip("/") + "/"
    lang = "zh-CN" if article_path.strip("/").startswith("zh/") else "en-US"
    section = "Symptoms" if "/symptoms/" in "/" + article_path else ("Treatments" if "/treatments/" in "/" + article_path else "TCM Basics")
    date_modified = time.strftime("%Y-%m-%d")
    additions = []
    if 'hreflang="x-default"' not in html_content:
        additions.append(f'<link rel="alternate" hreflang="x-default" href="{url}" />')
    if '<meta name="author"' not in html_content:
        additions.append('<meta name="author" content="SymptomCalm Editorial Team" />')
    if 'article:modified_time' not in html_content:
        additions.append(f'<meta property="article:modified_time" content="{date_modified}T00:00:00+00:00" />')
    if 'article:section' not in html_content:
        additions.append(f'<meta property="article:section" content="{section}" />')
    if additions:
        canonical = re.search(r'<link\b[^>]*rel=["\']canonical["\'][^>]*>', html_content, re.I)
        if not canonical:
            canonical = re.search(r'<link\b[^>]*href=["\'][^"\']+["\'][^>]*rel=["\']canonical["\'][^>]*>', html_content, re.I)
        if canonical:
            html_content = html_content[:canonical.end()] + "\n" + "\n".join(additions) + html_content[canonical.end():]
    if '"@type": "Organization"' not in html_content or '"@type": "MedicalWebPage"' not in html_content or '"dateModified"' not in html_content:
        title_match = re.search(r'<title\b[^>]*>(.*?)</title>', html_content, re.I | re.S)
        desc_match = re.search(r'<meta\b[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)', html_content, re.I)
        title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip() if title_match else "SymptomCalm article"
        description = html.unescape(desc_match.group(1)).strip() if desc_match else "Educational information about Traditional Chinese Medicine and everyday wellbeing."
        graph = {"@context":"https://schema.org","@graph":[
            {"@type":"Organization","@id":"https://symptomcalm.com/#organization","name":"SymptomCalm","url":"https://symptomcalm.com/","logo":{"@type":"ImageObject","url":"https://symptomcalm.com/favicon.svg"},"email":"contact@symptomcalm.com"},
            {"@type":"MedicalWebPage","@id":url+"#webpage","url":url,"name":title,"description":description,"publisher":{"@id":"https://symptomcalm.com/#organization"},"dateModified":date_modified,"inLanguage":lang}
        ]}
        block = '<script type="application/ld+json">\n' + json.dumps(graph, ensure_ascii=False, indent=2) + '\n</script>\n'
        html_content = re.sub(r'<!--FAQ_SCHEMA(?:_ZH)?-->', block + r'\g<0>', html_content, count=1, flags=re.I)
    return html_content



def validate_identity(html_content, article_path):
    """Refuse to write HTML whose declared identity belongs to another URL."""
    expected = "https://symptomcalm.com/" + str(article_path).strip("/") + "/"
    canonical = re.search(r"<link\b[^>]*rel=[\"']canonical[\"'][^>]*href=[\"']([^\"']+)", html_content, re.I)
    if not canonical:
        canonical = re.search(r"<link\b[^>]*href=[\"']([^\"']+)[\"'][^>]*rel=[\"']canonical", html_content, re.I)
    if not canonical or canonical.group(1).rstrip("/") != expected.rstrip("/"):
        got = canonical.group(1) if canonical else "MISSING"
        raise ValueError(f"identity gate: canonical {got!r} != expected {expected!r}")
    ogurl = re.search(r"<meta\b[^>]*property=[\"']og:url[\"'][^>]*content=[\"']([^\"']+)", html_content, re.I)
    if ogurl and ogurl.group(1).rstrip("/") != expected.rstrip("/"):
        raise ValueError(f"identity gate: og:url {ogurl.group(1)!r} != expected {expected!r}")
    if len(re.findall(r'<h1\b', html_content, re.I)) != 1:
        raise ValueError("identity gate: expected exactly one H1")
    title = re.search(r'<title\b[^>]*>(.*?)</title>', html_content, re.I|re.S)
    if not title or not re.sub(r'<[^>]+>', '', title.group(1)).strip():
        raise ValueError("identity gate: missing title")



def publish(html_content_file: str):
    """Publish an article from an HTML content file."""
    data = load_queue()
    if not data["queue"]:
        print("ERROR: Queue is empty, nothing to publish")
        return 1

    item = data["queue"][0]
    article_rel = item["path"].lstrip("/")
    article_file = WORKDIR / article_rel / "index.html"

    # Read the HTML content from the specified file
    try:
        with open(html_content_file) as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"ERROR: HTML content file not found: {html_content_file}", file=sys.stderr)
        return 1

    # Normalize required metadata before identity and release-gate checks.
    html_content = ensure_release_metadata(html_content, item["path"])

    # Identity gate must pass before touching the target file.
    try:
        validate_identity(html_content, item["path"])
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    # Ensure directory exists
    article_file.parent.mkdir(parents=True, exist_ok=True)

    # Write the article HTML
    with open(article_file, "w") as f:
        f.write(html_content)
    print(f"Article written: {article_file}")

    # Update sitemap
    update_sitemap(Path(item["path"]))

    # Mark as published
    data["published"].append({**item, "published_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    data["queue"].pop(0)
    save_queue(data)
    print(f"Queue updated: {item['path']} → published")

    # The batch auto-publisher owns the transaction and Git operations. Keep
    # single-article CLI compatibility, but never let a batch publish create
    # partial commits or pushes before the full-site release gates run.
    if os.environ.get("AUTO_PUBLISH_BATCH") == "1":
        print("Git commit/push deferred to outer batch transaction")
        return 0

    success = commit_and_push(article_file)
    if success:
        print("Git push succeeded")
    else:
        print("WARNING: Git push may have failed", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} next | publish <html_content_file>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "next":
        item = get_next()
        if item:
            print(json.dumps(item, indent=2))
        else:
            print(json.dumps(None))
        sys.exit(0)

    elif command == "publish":
        if len(sys.argv) < 3:
            print(f"Usage: {sys.argv[0]} publish <html_content_file>", file=sys.stderr)
            sys.exit(1)
        rc = publish(sys.argv[2])
        sys.exit(rc)

    elif command == "remaining":
        print(queue_remaining())
        sys.exit(0)

    elif command == "add":
        # Read JSON from stdin and add to queue
        new_items = json.load(sys.stdin)
        if isinstance(new_items, dict):
            new_items = [new_items]
        add_to_queue(new_items)
        sys.exit(0)

    elif command == "status":
        data = load_queue()
        print(f"Queue: {len(data['queue'])} remaining, {len(data['published'])} published")
        if data["queue"]:
            print(f"Next: id={data['queue'][0]['id']} {data['queue'][0]['path']}")
        sys.exit(0)

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)
