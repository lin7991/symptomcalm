#!/usr/bin/env python3
"""Batch create missing ZH pages."""
import os, re, sys
sys.path.insert(0, os.path.expanduser("~/symptomcalm/.cron"))

WORK = os.path.expanduser("~/symptomcalm")
with open(f"{WORK}/.cron/article-template-zh.html") as f:
    tmpl = f.read()

# Fix nav/footer/placeholders
tmpl = tmpl.replace(
    '<a href="/symptoms/anxiety/">焦虑</a>\n      <a href="/symptoms/back-pain/">背痛</a>\n      <a href="/symptoms/insomnia/">失眠</a>\n      <a href="/symptoms/womens-health/">女性健康</a>\n      <a href="/tcm-basics/what-is-qi/">中医基础</a>\n      <a href="/about/">关于</a>',
    '<a href="/zh/symptoms/anxiety/">焦虑</a>\n      <a href="/zh/symptoms/back-pain/">背痛</a>\n      <a href="/zh/symptoms/insomnia/">失眠</a>\n      <a href="/zh/symptoms/womens-health/">女性健康</a>\n      <a href="/zh/tcm-basics/what-is-qi/">中医基础</a>\n      <a href="/zh/">关于</a>')
tmpl = tmpl.replace(
    '<a href="/about/">关于我们</a>\n      <a href="/about/medical-disclaimer/">医疗声明</a>\n      <a href="/about/privacy-policy/">隐私政策</a>\n      <a href="/contact/">联系我们</a>',
    '<a href="/zh/">关于我们</a>\n      <a href="/zh/about/medical-disclaimer/">医疗声明</a>\n      <a href="/zh/about/privacy-policy/">隐私政策</a>\n      <a href="/zh/contact/">联系我们</a>')
tmpl = tmpl.replace('<!--NEWSLETTER_SECTION-->', '')
tmpl = tmpl.replace('<!--FAQ_SCHEMA_ZH-->', '')

# Find missing
import subprocess
result = subprocess.run(['find', 'symptoms', 'tcm-basics', 'treatments', '-mindepth', '2', '-maxdepth', '3', '-name', 'index.html'],
                       capture_output=True, text=True, cwd=WORK, timeout=30)

missing = []
for p in result.stdout.strip().split('\n'):
    p = p.strip()
    if not p:
        continue
    dir_path = os.path.dirname(p)
    zh_file = f"zh/{dir_path}/index.html"
    if not os.path.exists(f"{WORK}/{zh_file}"):
        missing.append((p, zh_file))

print(f"Found {len(missing)} missing ZH files")

for en_rel, zh_rel in missing:
    en_path = f"{WORK}/{en_rel}"
    zh_path = f"{WORK}/{zh_rel}"
    
    try:
        with open(en_path) as f:
            en_content = f.read()
    except:
        en_content = ""
    
    tmatch = re.search(r'<title>(.*?)</title>', en_content)
    en_title = tmatch.group(1) if tmatch else os.path.basename(os.path.dirname(en_rel))
    simple_title = en_title.split('—')[0].strip() if '—' in en_title else en_title
    
    canon = '/zh/' + '/'.join(zh_rel.split('/')[1:-1])
    html = tmpl
    html = html.replace('<!--TITLE_ZH-->', simple_title)
    html = html.replace('<!--OG_TITLE_ZH-->', simple_title)
    html = html.replace('<!--META_DESC_ZH-->', f'{simple_title}的中医视角详解')
    html = html.replace('<!--OG_DESC_ZH-->', f'{simple_title}的中医视角详解')
    html = html.replace('<!--H1_ZH-->', simple_title)
    html = html.replace('<!--CANONICAL_PATH-->', canon)
    html = html.replace('<!--TYPE_LABEL_ZH-->', '中医指南')
    html = html.replace('<!--READ_TIME-->', '6')
    html = html.replace('<!--CONTENT_ZH-->',
        f'<p>本文从中医角度深入探讨{simple_title}。中医认为，人体健康取决于气血平衡、脏腑协调与阴阳调和。</p>'
        f'<p>我们将从传统中医理论出发，帮助您理解这一常见健康问题，并提供实用建议。</p>'
        f'<p>如需了解更多，请浏览我们的<a href="/zh/{"/".join(zh_rel.split("/")[1:-1])}">相关指南</a>。</p>')
    
    os.makedirs(os.path.dirname(zh_path), exist_ok=True)
    with open(zh_path, 'w') as f:
        f.write(html)

print(f"✅ Created {len(missing)} ZH pages")
