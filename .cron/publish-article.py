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

import json, os, shutil, subprocess, sys, time
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


def commit_and_push(article_path):
    """Git commit and push the new article."""
    os.chdir(WORKDIR)
    result = subprocess.run(
        ["git", "add", str(article_path), str(SITEMAP_FILE), str(QUEUE_FILE)],
        capture_output=True, text=True
    )
    article_id = article_path.relative_to(WORKDIR)
    commit_msg = f"Auto-publish: {article_id}"
    result = subprocess.run(
        ["git", "commit", "-m", commit_msg],
        capture_output=True, text=True
    )
    if result.returncode != 0 and "nothing to commit" not in result.stderr:
        print(f"Commit warning: {result.stderr}", file=sys.stderr)

    result = subprocess.run(
        ["git", "push", "origin", "main"],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        # Try pull+push if rejected
        subprocess.run(["git", "pull", "--rebase", "origin", "main"],
                       capture_output=True, text=True, timeout=30)
        result = subprocess.run(
            ["git", "push", "origin", "main"],
            capture_output=True, text=True, timeout=30
        )
    return result.returncode == 0


def update_sitemap(article_path):
    """Add the new article URL to sitemap.xml."""
    url = f"https://symptomcalm.com{article_path}/"
    with open(SITEMAP_FILE) as f:
        content = f.read()

    # Insert before closing </urlset>
    insert = f"""  <url>
    <loc>{url}</loc>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>"""

    if url not in content:
        content = content.replace("</urlset>", f"{insert}\n</urlset>")
        with open(SITEMAP_FILE, "w") as f:
            f.write(content)
        print(f"Sitemap updated: {url}")
    else:
        print(f"Sitemap unchanged: {url} already exists")


def ensure_parent_dir(path: Path):
    """Create parent directories if they don't exist."""
    path.parent.mkdir(parents=True, exist_ok=True)


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

    # Ensure directory exists
    article_file.parent.mkdir(parents=True, exist_ok=True)

    # Write the article HTML
    with open(article_file, "w") as f:
        f.write(html_content)
    print(f"Article written: {article_file}")

    # Update sitemap
    update_sitemap(Path(item["path"]))

    # Mark as published
    data["published"].append(item)
    data["queue"].pop(0)
    save_queue(data)
    print(f"Queue updated: {item['path']} → published")

    # Git commit and push
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
