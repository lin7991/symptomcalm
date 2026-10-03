#!/usr/bin/env python3
"""Refresh canonical metadata, hreflang, GEO/SEO fields, and JSON-LD sitewide."""
import html, json, os, re
from datetime import date
from pathlib import Path

WORK = Path(os.environ.get("WORKDIR", os.path.expanduser("~/symptomcalm")))
BASE = "https://symptomcalm.com"
TODAY = date.today().isoformat()
EN_NAMES = {
    "symptoms":"Symptoms", "tcm-basics":"TCM Basics", "treatments":"Treatments",
    "about":"About", "contact":"Contact", "anxiety":"Anxiety", "back-pain":"Back Pain",
    "insomnia":"Insomnia", "digestion":"Digestion", "fatigue":"Fatigue", "headaches":"Headaches",
    "allergies":"Allergies", "skin-conditions":"Skin Conditions", "womens-health":"Women's Health",
    "joint-pain":"Joint Pain", "stress":"Stress", "respiratory-health":"Respiratory Health",
    "mental-emotional-health":"Mental & Emotional Health", "eye-health":"Eye Health",
    "ear-health-tinnitus":"Ear Health & Tinnitus",
}
ZH_NAMES = {
    "symptoms":"症状", "tcm-basics":"中医基础", "treatments":"疗法", "about":"关于",
    "contact":"联系我们", "anxiety":"焦虑", "back-pain":"背痛", "insomnia":"失眠",
    "digestion":"消化", "fatigue":"疲劳", "headaches":"头痛", "allergies":"过敏",
    "skin-conditions":"皮肤", "womens-health":"女性健康", "joint-pain":"关节",
    "stress":"压力", "respiratory-health":"呼吸健康", "mental-emotional-health":"心理与情绪",
    "eye-health":"眼部健康", "ear-health-tinnitus":"耳鸣",
}

def attr(html_text, name, value):
    pat = re.compile(r'(<meta\s+name="' + re.escape(name) + r'"\s+content=")[^"]*("\s*/?>)', re.I)
    safe_value = html.escape(value, quote=True)
    if pat.search(html_text):
        return pat.sub(lambda m: m.group(1) + safe_value + m.group(2), html_text, count=1)
    return html_text.replace('</head>', f'  <meta name="{name}" content="{safe_value}" />\n</head>', 1)

def prop(html_text, name, value):
    pat = re.compile(r'(<meta\s+property="' + re.escape(name) + r'"\s+content=")[^"]*("\s*/?>)', re.I)
    safe_value = html.escape(value, quote=True)
    if pat.search(html_text):
        # Callable replacement prevents a leading date/year digit from merging with \1.
        return pat.sub(lambda m: m.group(1) + safe_value + m.group(2), html_text, count=1)
    return html_text.replace('</head>', f'  <meta property="{name}" content="{safe_value}" />\n</head>', 1)

def link_alternates(text, links):
    text = re.sub(r'\s*<link\s+rel="alternate"\s+hreflang="[^"]+"[^>]*>', '', text, flags=re.I)
    block = ''.join(f'  <link rel="alternate" hreflang="{lang}" href="{url}" />\n' for lang, url in links)
    return text.replace('</head>', block + '</head>', 1)

def canonical_path(rel):
    s = rel.as_posix()
    if s == 'index.html': return '/'
    if s.startswith('zh/index.html'): return '/zh/'
    if s.endswith('/index.html'): return '/' + s[:-10].strip('/') + '/'
    return '/' + s

def rebuild(rel, text):
    # Remove date-only remnants left by the historical bad replacement-string bug.
    text = re.sub(r'\s*P\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+\d{2}:\d{2}"\s*/>', '', text)
    is_zh = rel.as_posix().startswith('zh/')
    path = canonical_path(rel)
    url = BASE + path
    en_path = path[3:] if path.startswith('/zh/') else path
    en_url = BASE + (en_path or '/')
    zh_url = BASE + ('/zh' + en_path if en_path != '/' else '/zh/')
    title_m = re.search(r'<title>(.*?)</title>', text, re.I|re.S)
    title = html.unescape(re.sub(r'<[^>]+>', '', title_m.group(1))).strip() if title_m else 'SymptomCalm'
    desc_m = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', text, re.I)
    desc = html.unescape(desc_m.group(1)).strip() if desc_m else 'Educational explanations of Traditional Chinese Medicine for curious readers.'
    lang = 'zh-CN' if is_zh else 'en-US'
    parts = [p for p in rel.parts[:-1] if p != 'zh']
    names = ZH_NAMES if is_zh else EN_NAMES
    crumbs = [{"@type":"ListItem","position":1,"name":"首页" if is_zh else "Home","item":BASE+('/zh/' if is_zh else '/')}]
    cur = '/zh' if is_zh else ''
    for i, part in enumerate(parts, 2):
        cur += '/' + part
        crumbs.append({"@type":"ListItem","position":i,"name":names.get(part, part.replace('-',' ').title()),"item":BASE+cur+'/'})
    has_zh = (WORK / ('zh' + en_path + 'index.html' if en_path != '/' else 'zh/index.html')).exists()
    links = [('en', en_url)] if is_zh else []
    if not is_zh and has_zh: links.append(('zh', zh_url))
    links.append(('x-default', en_url))
    text = re.sub(r'\s*<link\s+rel="canonical"\s+[^>]*>', '', text, flags=re.I)
    text = text.replace('</head>', f'  <link rel="canonical" href="{url}" />\n</head>', 1)
    text = link_alternates(text, links)
    text = attr(text, 'author', 'SymptomCalm Editorial Team')
    text = prop(text, 'og:site_name', 'SymptomCalm')
    text = prop(text, 'og:locale', lang)
    text = prop(text, 'article:modified_time', TODAY + 'T00:00:00+00:00')
    text = prop(text, 'article:section', names.get(parts[0], 'TCM Health Education') if parts else 'TCM Health Education')
    # Remove all generated LD+JSON and replace with one coherent, entity-rich graph.
    text = re.sub(r'\s*<script type="application/ld\+json">.*?</script>', '', text, flags=re.I|re.S)
    graph = {
      "@context":"https://schema.org",
      "@graph":[
        {"@type":"Organization","@id":BASE+"/#organization","name":"SymptomCalm","url":BASE+"/","logo":{"@type":"ImageObject","url":BASE+"/favicon.svg"},"email":"contact@symptomcalm.com"},
        {"@type":"WebSite","@id":BASE+"/#website","name":"SymptomCalm","url":BASE+"/","publisher":{"@id":BASE+"/#organization"},"inLanguage":lang},
        {"@type":"BreadcrumbList","itemListElement":crumbs},
        {"@type":"MedicalWebPage","@id":url+"#webpage","url":url,"name":title,"description":desc,"inLanguage":lang,"isPartOf":{"@id":BASE+"/#website"},"publisher":{"@id":BASE+"/#organization"},"about":{"@type":"Thing","name":"Traditional Chinese Medicine"},"dateModified":TODAY},
        {"@type":"Article","@id":url+"#article","headline":title.replace(' — SymptomCalm',''),"description":desc,"author":{"@type":"Organization","name":"SymptomCalm Editorial Team","url":BASE+"/about/"},"publisher":{"@id":BASE+"/#organization"},"datePublished":"2026-06-01","dateModified":TODAY,"mainEntityOfPage":{"@id":url+"#webpage"},"inLanguage":lang}
      ]
    }
    block = '  <script type="application/ld+json">\n' + json.dumps(graph, ensure_ascii=False, indent=2) + '\n  </script>\n'
    text = text.replace('</head>', block + '</head>', 1)
    return text

def main():
    changed = 0
    for f in sorted(WORK.rglob('index.html')):
        rel = f.relative_to(WORK)
        if any(x in rel.parts for x in ('.git','node_modules','.cron')): continue
        old = f.read_text(encoding='utf-8', errors='replace')
        new = rebuild(rel, old)
        if new != old:
            f.write_text(new, encoding='utf-8'); changed += 1
    print(f'REFRESH_SEO_UPDATED={changed}')

if __name__ == '__main__': main()
