#!/usr/bin/env python3
"""Generate feed.xml (RSS) from the content queue's published list.

Why not git log --name-only: a batch commit touching hundreds of files
(e.g. FAQ schema whitespace sweep) floods the file list alphabetically,
pushing real new articles out of the top-20 (2026-08-31: sunday-scaries-tcm
published but missing from feed.xml). The queue's `published` array holds
the true publish order with real titles.
"""
import json, os, re, subprocess
from datetime import datetime, timezone
from pathlib import Path

WORK = Path(os.path.expanduser("~/symptomcalm"))
QUEUE = WORK / '.content-queue.json'


def _git_date(path):
    """Return author date of the commit that FIRST added path (publish time, UTC)."""
    try:
        r = subprocess.run(
            ['git', 'log', '-1', '--diff-filter=A', '--format=%ai', '--', path],
            capture_output=True, text=True, timeout=15, cwd=WORK
        )
        return r.stdout.strip() or None
    except Exception:
        return None


def get_recent_articles(limit=20):
    """Get the most recent published articles from the content queue."""
    with open(QUEUE) as f:
        q = json.load(f)
    published = q.get('published', [])

    articles = []
    for item in published[-limit:][::-1]:  # newest first
        path = item.get('path', '').lstrip('/').rstrip('/')
        if not path:
            continue
        title = (item.get('title') or '').strip() or "SymptomCalm Article"
        url = f"https://symptomcalm.com/{path}/"
        date = _git_date(path + '/index.html') or datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %z')
        articles.append({'url': url, 'title': title, 'date': date})
    return articles


def build_rss(articles):
    """Build RSS XML."""
    now = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')

    items = ""
    for a in articles:
        pub_date = a['date'].replace(' ', 'T')
        # Python <3.11 fromisoformat requires ':' in tz offset (+08:00, not +0800)
        pub_date = re.sub(r'([+-]\d{2})(\d{2})$', r'\1:\2', pub_date)
        try:
            dt = datetime.fromisoformat(pub_date)
            rss_date = dt.astimezone(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')
        except Exception:
            rss_date = now

        title = a['title'] or "SymptomCalm Article"
        items += f"""    <item>
      <title><![CDATA[{title}]]></title>
      <link>{a['url']}</link>
      <guid>{a['url']}</guid>
      <pubDate>{rss_date}</pubDate>
      <description><![CDATA[Explore {title} through the lens of Traditional Chinese Medicine at SymptomCalm.]]></description>
    </item>
"""

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>SymptomCalm — TCM Health Insights</title>
    <link>https://symptomcalm.com/</link>
    <description>Understand your symptoms through the lens of Traditional Chinese Medicine. No jargon, no miracle claims — clear, grounded wisdom.</description>
    <language>en-us</language>
    <lastBuildDate>{now}</lastBuildDate>
    <atom:link href="https://symptomcalm.com/feed.xml" rel="self" type="application/rss+xml"/>
{items}  </channel>
</rss>
'''


def main():
    articles = get_recent_articles()
    rss = build_rss(articles)
    with open(WORK / 'feed.xml', 'w') as f:
        f.write(rss)
    print(f"✅ Generated feed.xml with {len(articles)} recent articles")


if __name__ == "__main__":
    main()
