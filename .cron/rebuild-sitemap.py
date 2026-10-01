#!/usr/bin/env python3
"""Rebuild sitemap.xml from actual pages with canonical URLs and lastmod dates."""
from datetime import date
from pathlib import Path
import os, re

ROOT=Path(os.environ.get('WORKDIR',Path(__file__).resolve().parents[1]))
BASE='https://symptomcalm.com'
urls=[]
for f in sorted(ROOT.rglob('index.html')):
    rel=f.relative_to(ROOT)
    if any(x in rel.parts for x in ('.git','node_modules','.cron')): continue
    s=rel.as_posix()
    if s=='index.html': path='/'
    elif s.endswith('/index.html'): path='/' + s[:-10].strip('/') + '/'
    else: continue
    urls.append((path,date.fromtimestamp(f.stat().st_mtime).isoformat()))
# unique canonical URLs, excluding malformed index.html URLs
seen=set(); rows=[]
for path,lastmod in urls:
    if path in seen or 'index.html' in path: continue
    seen.add(path); rows.append(f'  <url>\n    <loc>{BASE}{path}</loc>\n    <lastmod>{lastmod}</lastmod>\n    <changefreq>monthly</changefreq>\n    <priority>{"1.0" if path in ("/","/zh/") else "0.7"}</priority>\n  </url>')
out='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+'\n'.join(rows)+'\n</urlset>\n'
(ROOT/'sitemap.xml').write_text(out,encoding='utf-8')
print(f'SITEMAP_URLS={len(rows)}')
print('BAD_INDEX_URLS=',out.count('index.html'))
