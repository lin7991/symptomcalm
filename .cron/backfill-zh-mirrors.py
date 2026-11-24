#!/usr/bin/env python3
"""Backfill missing ZH mirrors only for queue-recorded published EN articles."""
import html, json, os, re, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / ".content-queue.json"
TEMPLATE = ROOT / ".cron" / "article-template-zh.html"
LOG = ROOT / ".cron" / "backfill-zh.log"
HERMES = ["hermes", "-p", "symptomcalm", "chat", "-Q", "--source", "tool", "--query-file", "-"]


def query(prompt, timeout):
    last = ""
    for attempt in range(1, 4):
        try:
            r = subprocess.run(HERMES, input=prompt, text=True, capture_output=True,
                               cwd=ROOT, timeout=timeout)
            out = r.stdout.strip()
            if out:
                if out.startswith("```"):
                    out = re.sub(r"^```(?:html|json)?\s*", "", out, flags=re.I)
                    out = re.sub(r"\s*```$", "", out)
                return out.strip()
            last = r.stderr.strip() or "empty Hermes output"
        except (subprocess.TimeoutExpired, BrokenPipeError, OSError) as exc:
            last = str(exc)
        time.sleep(attempt * 3)
    raise RuntimeError(last)


def extract(en, rel):
    def one(pattern, default=""):
        m = re.search(pattern, en, re.I | re.S)
        return html.unescape(m.group(1).strip()) if m else default
    body = re.search(r'<div class="article-body">(.*?)</div>\s*</article>', en, re.I | re.S)
    if not body:
        raise ValueError(f"article body not found: {rel}")
    meta = re.search(r'<div class="meta">(.*?)\s*·\s*(\d+)\s+min read</div>', en, re.I | re.S)
    canon = one(r'<link\b[^>]*rel=["\']canonical["\'][^>]*href=["\']https://symptomcalm\.com([^"\']+)', "/" + rel)
    return {
        "title": one(r'<title\b[^>]*>(.*?)\s+—\s+SymptomCalm</title>'),
        "desc": one(r'<meta\b[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)'),
        "h1": one(r'<h1\b[^>]*>(.*?)</h1>'),
        "type": html.unescape(meta.group(1).strip()) if meta else "Guide",
        "read": meta.group(2) if meta else "8",
        "canon": canon if canon.startswith("/") else "/" + canon,
        "body": body.group(1).strip(),
    }


def metadata(m):
    prompt = f'''Translate this TCM article metadata into natural Simplified Chinese. Return ONLY valid JSON with exactly these keys: zh_title, zh_desc, zh_h1, zh_type.
Title: {m["title"]}
Description: {m["desc"]}
H1: {m["h1"]}
Type: {m["type"]}
Rules: preserve the meaning; keep Qi, Yin, Yang, Spleen, Kidney, Liver, Lung, Blood, Jing, Shen in English when used as TCM terms; zh_type should be a concise label such as 症状指南、综合指南、中医基础、传统方法指南.''' 
    raw = query(prompt, 90)
    match = re.search(r'\{.*\}', raw, re.S)
    if not match:
        raise ValueError("metadata JSON missing")
    d = json.loads(match.group(0))
    if not all(d.get(k, '').strip() for k in ('zh_title','zh_desc','zh_h1','zh_type')):
        raise ValueError("metadata field empty")
    return d


def translate_body(m, rel):
    prompt = f'''Translate the following complete TCM article body from English into polished Simplified Chinese for a Western audience.
Keep every HTML tag, heading structure, class name, href value, URL, anchor target, and measurement unit exactly unchanged. Translate only visible English text. Do not add or remove sections. Preserve safety disclaimers, evidence limitations, and medical red flags accurately. Keep TCM terms such as Qi, Yin, Yang, Spleen, Kidney, Liver, Lung, Blood, Jing, Shen, Dampness, and Phlegm in English where they function as technical terms. Return ONLY HTML, with no markdown fences or commentary.
Article path: /{rel}/

HTML BODY:
{m["body"]}'''
    out = query(prompt, 360)
    if len(re.findall(r'<(?:h2|p|ul|ol|div|blockquote)\b', out, re.I)) < 2:
        raise ValueError("translated body too short or lost HTML structure")
    return out


def make_page(rel, en, zhmeta, body, m):
    tpl = TEMPLATE.read_text(encoding='utf-8')
    url = f"https://symptomcalm.com/zh/{rel}/"
    enurl = f"https://symptomcalm.com/{rel}/"
    date = time.strftime('%Y-%m-%d')
    section = 'Symptoms' if '/symptoms/' in '/' + rel else ('Treatments' if '/treatments/' in '/' + rel else 'TCM Basics')
    additions = f'''  <link rel="alternate" hreflang="x-default" href="{enurl}" />
  <meta name="author" content="SymptomCalm Editorial Team" />
  <meta property="article:modified_time" content="{date}T00:00:00+00:00" />
  <meta property="article:section" content="{section}" />'''
    graph = {"@context":"https://schema.org","@graph":[
        {"@type":"Organization","@id":"https://symptomcalm.com/#organization","name":"SymptomCalm","url":"https://symptomcalm.com/","logo":{"@type":"ImageObject","url":"https://symptomcalm.com/favicon.svg"},"email":"contact@symptomcalm.com"},
        {"@type":"MedicalWebPage","@id":url+"#webpage","url":url,"name":zhmeta['zh_title'],"description":zhmeta['zh_desc'],"publisher":{"@id":"https://symptomcalm.com/#organization"},"dateModified":date,"inLanguage":"zh-CN"},
        {"@type":"Article","@id":url+"#article","headline":zhmeta['zh_title'],"description":zhmeta['zh_desc'],"inLanguage":"zh-CN","author":{"@type":"Organization","name":"SymptomCalm Editorial Team"},"publisher":{"@id":"https://symptomcalm.com/#organization"},"dateModified":date,"mainEntityOfPage":{"@id":url+"#webpage"}}
    ]}
    block = '<script type="application/ld+json">\n' + json.dumps(graph, ensure_ascii=False, indent=2) + '\n</script>\n'
    tpl = tpl.replace('<!--TITLE_ZH-->', zhmeta['zh_title']).replace('<!--META_DESC_ZH-->', zhmeta['zh_desc']).replace('<!--OG_TITLE_ZH-->', zhmeta['zh_title']).replace('<!--OG_DESC_ZH-->', zhmeta['zh_desc']).replace('<!--H1_ZH-->', zhmeta['zh_h1']).replace('<!--TYPE_LABEL_ZH-->', zhmeta['zh_type']).replace('<!--READ_TIME-->', m['read']).replace('<!--CONTENT_ZH-->', body).replace('<!--CANONICAL_PATH-->', '/' + rel)
    tpl = tpl.replace('</head>', additions + '\n' + block + '</head>', 1)
    # Add the missing reciprocal language link using the resolved path.
    tpl = tpl.replace(f'hreflang="en" href="{enurl}"', f'hreflang="en" href="{enurl}"')
    return tpl


def targets():
    snapshot = ROOT / ".cron" / "backfill-targets.txt"
    if snapshot.exists():
        return [x.strip() for x in snapshot.read_text(encoding='utf-8').splitlines() if x.strip()]
    d = json.loads(QUEUE.read_text(encoding='utf-8'))
    out=[]
    for item in d.get('published', []):
        rel=item.get('path','').strip('/')
        if not rel or not rel.startswith(('symptoms/','treatments/','tcm-basics/')): continue
        en=ROOT/rel/'index.html'; zh=ROOT/'zh'/rel/'index.html'
        if en.exists() and not zh.exists(): out.append(rel)
    return sorted(set(out))


def main():
    todo=targets(); print(f'TARGETS={len(todo)}')
    start=int(os.environ.get('BACKFILL_START','0')); end=int(os.environ.get('BACKFILL_END',str(len(todo))))
    todo=todo[start:end]
    ok=0; fail=0
    for i,rel in enumerate(todo,start+1):
        try:
            en=(ROOT/rel/'index.html').read_text(encoding='utf-8')
            m=extract(en,rel); md=metadata(m); body=translate_body(m,rel); page=make_page(rel,en,md,body,m)
            if 'noindex' in page.lower() or 'Cloudflare Web Analytics' not in page or page.count('<h1') != 1: raise ValueError('page validation failed')
            out=ROOT/'zh'/rel/'index.html'; out.parent.mkdir(parents=True,exist_ok=True)
            fd,tmp=tempfile.mkstemp(prefix='.zh-',dir=str(out.parent)); os.close(fd)
            Path(tmp).write_text(page,encoding='utf-8'); os.replace(tmp,out)
            with LOG.open('a',encoding='utf-8') as f: f.write(f'OK {rel}\n')
            print(f'OK [{i}] {rel}', flush=True); ok+=1
        except Exception as e:
            with LOG.open('a',encoding='utf-8') as f: f.write(f'FAIL {rel}: {e}\n')
            print(f'FAIL [{i}] {rel}: {e}', file=sys.stderr, flush=True); fail+=1
    print(f'COMPLETE OK={ok} FAIL={fail} RANGE={start}:{end}')
    return 1 if fail else 0

if __name__=='__main__': raise SystemExit(main())
