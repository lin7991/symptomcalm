#!/usr/bin/env python3
"""Generate feed.xml (RSS) from git history + sitemap."""
import os, re, subprocess
from datetime import datetime, timezone
from pathlib import Path

WORK = Path(os.path.expanduser("~/symptomcalm"))

def get_recent_articles(limit=20):
    """Get recent article URLs + titles from git log."""
    os.chdir(WORK)
    result = subprocess.run(
        ['git', 'log', '--since=30 days ago', '--name-only', '--pretty=format:%H|%s|%ai', '--', 'symptoms/', 'tcm-basics/', 'treatments/'],
        capture_output=True, text=True, timeout=30
    )
    
    articles = []
    current = None
    for line in result.stdout.split('\n'):
        if '|' in line and len(line.split('|')) == 3:
            current = line.split('|')
        elif line.endswith('/index.html') and not line.startswith('zh/'):
            if current:
                articles.append({
                    'url': f"https://symptomcalm.com/{line.replace('index.html','')}",
                    'title': current[1].replace('Auto-publish: ', '').replace('Auto publish EN+ZH + FAQ', '').strip(),
                    'date': current[2]
                })
    
    # Deduplicate
    seen = set()
    deduped = []
    for a in articles:
        if a['url'] not in seen:
            seen.add(a['url'])
            deduped.append(a)
    
    return deduped[:limit]

def build_rss(articles):
    """Build RSS XML."""
    now = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')
    
    items = ""
    for a in articles:
        pub_date = a['date'].replace(' ', 'T') + 'Z'
        try:
            dt = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
            rss_date = dt.strftime('%a, %d %b %Y %H:%M:%S +0000')
        except:
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
