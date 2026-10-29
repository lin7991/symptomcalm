#!/usr/bin/env python3
"""Weekly SEO + GEO audit for SymptomCalm.

Read-only: scans the checked-out site and the live sitemap/robots, then writes
JSON + Markdown reports. GEO means answerability, source transparency, entity
consistency, and machine-readable page identity—not rankings guarantees.
"""
from __future__ import annotations
import concurrent.futures, hashlib, html, json, re, sys, urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / ".cron" / "reports"
BASE = "https://symptomcalm.com"
SITEMAP_URL = BASE + "/sitemap.xml"
UA = "SymptomCalm-Weekly-Audit/1.0"

def fetch(url, timeout=25):
    try:
        req=urllib.request.Request(url, headers={"User-Agent":UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"

def attr(tag, name):
    m=re.search(rf'\b{name}\s*=\s*(["\'])(.*?)\1', tag, re.I|re.S)
    return html.unescape(m.group(2).strip()) if m else ""

def first(pattern, text):
    m=re.search(pattern, text, re.I|re.S)
    if not m:
        return ""
    value = m.groups()[-1] if m.groups() else m.group(0)
    return html.unescape(re.sub(r"<[^>]+>", " ", value).strip())

def text_only(s):
    s=re.sub(r"<script.*?</script>|<style.*?</style>|<noscript.*?</noscript>"," ",s,flags=re.I|re.S)
    return re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",s)).strip()

def meta_content(t, key_type, key):
    for tag in re.findall(r"<meta\b[^>]*>", t, re.I|re.S):
        if re.search(rf"\b{key_type}=[\"']{re.escape(key)}[\"']", tag, re.I):
            m=re.search(r"\bcontent\s*=\s*([\"'])(.*?)\1", tag, re.I|re.S)
            if m: return html.unescape(m.group(2).strip())
    return ""

def page_info(path):
    t=path.read_text(encoding="utf-8",errors="replace")
    rel=path.relative_to(ROOT).as_posix()
    rel_dir = "" if rel == "index.html" else rel[:-10].rstrip("/")
    url=BASE + ("/" if not rel_dir else "/" + rel_dir + "/")
    can=first(r'<link\b[^>]*\brel=["\']canonical["\'][^>]*\bhref=["\']([^"\']+)',t)
    if not can:
        can=first(r'<link\b[^>]*\bhref=["\']([^"\']+)["\'][^>]*\brel=["\']canonical',t)
    title=first(r'<title\b[^>]*>(.*?)</title>',t)
    ogtitle=meta_content(t,"property","og:title")
    desc=meta_content(t,"name","description")
    ogdesc=meta_content(t,"property","og:description")
    h1=re.findall(r'<h1\b[^>]*>(.*?)</h1>',t,re.I|re.S)
    body=re.sub(r'<(script|style|nav|footer|header)\b.*?</\1>',' ',t,flags=re.I|re.S)
    words=len(re.findall(r"\b[A-Za-z][A-Za-z'-]*\b",text_only(body)))
    noindex=bool(re.search(r'<meta\b[^>]*name=["\']robots["\'][^>]*content=["\'][^"\']*noindex',t,re.I))
    refresh=bool(re.search(r'<meta\b[^>]*http-equiv=["\']refresh["\']',t,re.I))
    lang=first(r'<html\b[^>]*lang=["\']([^"\']+)',t)
    types=re.findall(r'"@type"\s*:\s*"([^"]+)"',t)
    hreflang=re.findall(r'<link\b[^>]*rel=["\']alternate["\'][^>]*hreflang=["\']([^"\']+)["\'][^>]*href=["\']([^"\']+)',t,re.I)
    return dict(path=rel,url=url,canonical=can,title=title,og_title=ogtitle,description=desc,og_description=ogdesc,h1=len(h1),words=words,noindex=noindex,refresh=refresh,lang=lang,types=types,hreflang=hreflang,body_hash=hashlib.sha256(text_only(body).lower().encode()).hexdigest())

def main():
    now=datetime.now(timezone.utc).isoformat()
    files=sorted(p for p in ROOT.rglob("index.html") if ".git" not in p.parts and ".cron" not in p.parts)
    pages=[page_info(p) for p in files]
    sitemap_status,sitemap=fetch(SITEMAP_URL)
    live_sitemap=sitemap
    local_sitemap = ROOT / "sitemap.xml"
    local_sitemap_text = local_sitemap.read_text(encoding="utf-8", errors="replace") if local_sitemap.exists() else ""
    if sitemap_status != 200:
        # GitHub Pages/Cloudflare can briefly return a WAF response to the
        # audit User-Agent. Never treat an empty live response as a clean site:
        # audit the checked-out sitemap and mark the source explicitly.
        sitemap = local_sitemap_text
        sitemap_status = "local-fallback"
    else:
        # Release gates must validate the artifact about to be committed, not a
        # stale CDN copy. Keep live fetch status for the report and compare it.
        sitemap = local_sitemap_text or sitemap
    live_urls=set(re.findall(r'<(?:\w+:)?loc>\s*(.*?)\s*</(?:\w+:)?loc>',sitemap,re.I|re.S))
    fetched_urls=set(re.findall(r'<(?:\w+:)?loc>\s*(.*?)\s*</(?:\w+:)?loc>',live_sitemap,re.I|re.S)) if sitemap_status != "local-fallback" else set()
    local_urls={p["url"] for p in pages if not p["noindex"] and not p["refresh"]}
    blocking=[]; warnings=[]
    for p in pages:
        if p["noindex"] and p["url"] in live_urls: blocking.append(("noindex_in_sitemap",p["path"]))
        if p["refresh"] and p["url"] in live_urls: blocking.append(("redirect_in_sitemap",p["path"]))
        if p["canonical"] and p["canonical"].rstrip("/") != p["url"].rstrip("/") and not p["refresh"] and not p["noindex"]: blocking.append(("canonical_mismatch",p["path"]))
        if not p["canonical"] and not p["refresh"]: blocking.append(("missing_canonical",p["path"]))
        if p["title"] != p["og_title"] and not p["refresh"]: warnings.append(("title_og_title_mismatch",p["path"]))
        if p["description"] != p["og_description"] and not p["refresh"]: warnings.append(("description_og_description_mismatch",p["path"]))
        if p["h1"] != 1 and not p["refresh"]: blocking.append(("h1_count",p["path"]))
        can_path = urlsplit(p["canonical"]).path if p["canonical"] else ""
        if "//" in can_path or can_path.endswith("//"): blocking.append(("malformed_canonical",p["path"]))
        if not p["refresh"] and not p["noindex"] and p["words"] < 600 and any(p["path"].startswith(x) for x in ("symptoms/","treatments/","tcm-basics/")): warnings.append(("short_article",p["path"]))
        if not p["refresh"] and "MedicalWebPage" not in p["types"]: warnings.append(("missing_medical_webpage_schema",p["path"]))
        if not p["refresh"] and not any(x in p["types"] for x in ("Article","FAQPage")): warnings.append(("weak_machine_readable_entity_schema",p["path"]))
        if not p["refresh"] and not p["lang"]: blocking.append(("missing_lang",p["path"]))
        if not p["refresh"] and not p["hreflang"]: warnings.append(("missing_hreflang",p["path"]))
    groups=defaultdict(list)
    for p in pages:
        if p["noindex"] or p["refresh"]: continue
        # Do not classify normal EN/ZH mirrors as same-language duplicates.
        key=(p["body_hash"], p["path"].startswith("zh/"))
        groups[key].append(p["path"])
    duplicate_groups=[v for v in groups.values() if len(v)>1]
    for g in duplicate_groups: blocking.append(("same_language_duplicate_body"," | ".join(g)))
    redirect_links=[]
    redirect_paths={p["url"] for p in pages if p["refresh"]}
    for path in files:
        t=path.read_text(encoding="utf-8",errors="replace")
        rel=path.relative_to(ROOT).as_posix()
        for href in re.findall(r'\bhref=["\']([^"\']+)["\']',t,re.I):
            if href.startswith(BASE) and href.rstrip("/")+"/" in redirect_paths: redirect_links.append((rel,href))
    for x in redirect_links: warnings.append(("internal_link_to_meta_redirect",f"{x[0]} -> {x[1]}"))
    report={"generated_at":now,"local_html":len(files),"sitemap_status":sitemap_status,"sitemap_urls":len(live_urls),"live_sitemap_urls":len(fetched_urls),"live_sitemap_stale": bool(fetched_urls and fetched_urls != live_urls),"local_indexable_urls":len(local_urls),"blocking_count":len(blocking),"warning_count":len(warnings),"duplicate_groups":duplicate_groups,"blocking":blocking,"warnings":warnings}
    REPORT_DIR.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now().strftime("%Y-%m-%d")
    (REPORT_DIR/f"weekly-seo-geo-{stamp}.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    lines=[f"# SymptomCalm Weekly SEO + GEO Audit — {stamp}","",f"Generated: {now}","",f"- Local HTML: {len(files)}",f"- Sitemap status: {sitemap_status}",f"- Sitemap URLs (local artifact): {len(live_urls)}",f"- Sitemap URLs (live fetch): {len(fetched_urls)}",f"- Live sitemap stale: {bool(fetched_urls and fetched_urls != live_urls)}",f"- Blocking defects: {len(blocking)}",f"- Warnings: {len(warnings)}","", "## Blocking defects"]
    lines += [f"- **{k}**: {v}" for k,v in blocking[:300]] or ["- None"]
    lines += ["", "## Warnings"] + ([f"- **{k}**: {v}" for k,v in warnings[:300]] or ["- None"])
    (REPORT_DIR/f"weekly-seo-geo-{stamp}.md").write_text("\n".join(lines)+"\n")
    print(f"WEEKLY_SEO_GEO_AUDIT local_html={len(files)} sitemap_urls={len(live_urls)} blocking={len(blocking)} warnings={len(warnings)}")
    print(f"REPORT={REPORT_DIR/f'weekly-seo-geo-{stamp}.md'}")
    return 1 if blocking or warnings else 0

if __name__ == "__main__": sys.exit(main())
