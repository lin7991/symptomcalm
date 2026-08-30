#!/usr/bin/env python3
"""
Batch translate articles from English to Chinese using Hermes API.
"""
import os, re, json, subprocess, sys, time

WORKDIR = "/Users/xj/symptomcalm"
HERMES_CHAT = ["hermes", "-p", "symptomcalm", "chat", "-q", "-Q", "--source", "tool"]

# Template for Chinese articles
TEMPLATE = '''<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{TITLE} — SymptomCalm</title>
  <meta name="description" content="{DESC}" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Serif+SC:wght@400;600;700&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="/styles/style.css" />
  <link rel="canonical" href="https://symptomcalm.com/zh{CANON}/" />
  <link rel="alternate" hreflang="en" href="https://symptomcalm.com{CANON}/" />
  <meta property="og:title" content="{OGTITLE}" />
  <meta property="og:description" content="{OGDESC}" />
  <meta property="og:url" content="https://symptomcalm.com/zh{CANON}/" />
  <meta property="og:type" content="website" />
  <meta property="og:image" content="https://symptomcalm.com/favicon.svg" />
  <meta name="twitter:card" content="summary_large_image" />
  <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": "SymptomCalm",
    "url": "https://symptomcalm.com/zh{CANON}/"
  }}
  </script>
  <style>
    body {{ font-family: 'Noto Serif SC', 'Inter', sans-serif; }}
    .article-body {{ font-size: 1.05rem; line-height: 1.9; }}
  </style>
</head>
<body>

<header class="site-header">
  <div class="header-inner">
    <a href="/" class="logo">Symptom<span>Calm</span></a>
    <nav class="main-nav">
      <a href="/zh/symptoms/anxiety/">焦虑</a>
      <a href="/zh/symptoms/back-pain/">背痛</a>
      <a href="/zh/symptoms/insomnia/">失眠</a>
      <a href="/zh/symptoms/womens-health/">女性健康</a>
      <a href="/zh/tcm-basics/what-is-qi/">中医基础</a>
      <a href="/zh/">关于</a>
      <button id="lang-toggle" class="lang-toggle">English</button>
    </nav>
  </div>
</header>

<article class="content" style="padding: 0 1.5rem;">

  <div class="article-header">
    <div class="disclaimer-banner">
      <strong>免责声明：</strong>本文仅供教育和信息参考之用，不构成医疗建议、诊断或治疗方案。如有健康问题，请务必咨询专业医疗人员。中医作为一种辅助健康方法，不应替代专业医疗护理。
    </div>
    <h1>{H1}</h1>
    <div class="meta">{TYPE} · {READTIME} 分钟阅读</div>
  </div>

  <div class="article-body">

{BODY}

  </div>
</article>

<!-- placeholder for future newsletter -->

<footer class="site-footer">
  <div class="footer-inner">
    <div>
      <strong style="color:white;font-size:1.1rem;">SymptomCalm</strong>
      <p style="margin-top:0.5rem;font-size:0.8rem;">Ancient wisdom. Modern clarity.</p>
    </div>
    <div class="footer-links">
      <a href="/zh/about/">关于我们</a>
      <a href="/zh/about/medical-disclaimer/">医疗声明</a>
      <a href="/zh/about/privacy-policy/">隐私政策</a>
      <a href="/zh/contact/">联系我们</a>
    </div>
  </div>
  <div class="footer-bottom">
    <p>© 2026 SymptomCalm. 保留所有权利。本网站仅供教育用途，不提供医疗建议。</p>
    <p style="margin-top:0.3rem;font-size:0.8rem;">联系: <a href="mailto:contact@symptomcalm.com" style="color:var(--accent-light);">contact@symptomcalm.com</a></p>
  </div>
</footer>

  <script src="/js/site.js"></script>
</body>
</html>'''

def find_missing():
    """Find all English articles without a zh/ counterpart"""
    missing = []
    for root_dir in ["symptoms", "tcm-basics", "treatments"]:
        root_path = os.path.join(WORKDIR, root_dir)
        if not os.path.isdir(root_path):
            continue
        for dirpath, dirnames, filenames in os.walk(root_path):
            if "index.html" not in filenames:
                continue
            rel = os.path.relpath(dirpath, WORKDIR)
            zh_path = os.path.join(WORKDIR, "zh", rel, "index.html")
            if not os.path.exists(zh_path):
                missing.append(rel)
    return sorted(missing)

def extract_en(html, rel):
    """Extract English metadata and body"""
    title_m = re.search(r'<title>(.*?) — SymptomCalm</title>', html)
    desc_m = re.search(r'<meta name="description" content="(.*?)"', html)
    h1_m = re.search(r'<h1>(.*?)</h1>', html)
    meta_m = re.search(r'<div class="meta">(.*?) · (\d+) min read</div>', html)
    canon_m = re.search(r'<link rel="canonical" href="https://symptomcalm\.com(/.*?)/"', html)
    body_m = re.search(r'<div class="article-body">(.*?)</div>\s*\n\s*</article>', html, re.DOTALL)
    if not body_m:
        body_m = re.search(r'<div class="article-body">(.*?)</div>', html, re.DOTALL)
    
    return {
        'en_title': (title_m and title_m.group(1)) or '',
        'en_desc': (desc_m and desc_m.group(1)) or '',
        'en_h1': (h1_m and h1_m.group(1)) or '',
        'en_type': (meta_m and meta_m.group(1)) or '综合指南',
        'readtime': (meta_m and meta_m.group(2)) or '8',
        'canon': (canon_m and canon_m.group(1)) or '/' + rel,
        'en_body': (body_m and body_m.group(1).strip()) or '',
    }

def translate_meta(en_title, en_desc, en_h1, en_type):
    """Translate metadata using hermes"""
    prompt = f"""Translate this TCM article metadata from English to Simplified Chinese. Return ONLY a JSON object, no other text.

{{
  "zh_title": "Chinese translation of: {en_title}",
  "zh_desc": "Chinese translation of: {en_desc}",
  "zh_h1": "Chinese translation of: {en_h1}",
  "zh_type": "Chinese translation of: {en_type} (use short phrases like 综合指南, 症状指南, 治疗指南, 中医基础)"
}}

IMPORTANT: 
- Keep terms like Qi, Yin, Yang, Spleen, Kidney, Liver, Lung, Blood in English
- zh_title should be concise, end without period
- zh_desc should be a compelling Chinese sentence
- zh_h1 is the main heading - keep it natural in Chinese
- zh_type is the article type label like 综合指南, 症状指南, 中医基础, 治疗指南, etc.
- Return ONLY valid JSON"""
    
    result = subprocess.run(HERMES_CHAT, input=prompt, capture_output=True, text=True, timeout=120, cwd=WORKDIR)
    out = result.stdout.strip()
    
    # Try to extract JSON
    jm = re.search(r'\{[^{}]*(?:zh_title|zh_desc|zh_h1|zh_type)[^{}]*\}', out, re.DOTALL)
    if jm:
        try:
            return json.loads(jm.group())
        except:
            pass
    
    # Fallback: try to find non-JSON structured output
    return {
        'zh_title': en_title,
        'zh_desc': en_desc,
        'zh_h1': en_h1,
        'zh_type': en_type
    }

def translate_body(en_body, context):
    """Translate article body using hermes"""
    # Truncate if too long (API limit)
    if len(en_body) > 12000:
        en_body = en_body[:12000]
    
    prompt = f"""Translate this TCM article body from English to Simplified Chinese. Keep ALL HTML tags exactly as-is. Only translate text content.

RULES:
1. Keep ALL HTML tags, class names, table structure, divs, spans, href values, URLs unchanged
2. Keep TCM terms in English: Qi, Yin, Yang, Spleen, Kidney, Liver, Lung, Blood, Jing, Shen, Dampness, Phlegm, Wei Qi, Governor Vessel, Bladder channel, Meridian, Acupoint, etc.
3. Keep ALL href values and links unchanged
4. Convert "X min read" to "X 分钟阅读" if present
5. Do NOT translate the newsletter form or container sections - leave them as-is or remove them
6. Return ONLY the translated HTML body, no extra text

CONTEXT: {context}

BODY TO TRANSLATE:
{en_body}"""
    
    result = subprocess.run(HERMES_CHAT, input=prompt, capture_output=True, text=True, timeout=300, cwd=WORKDIR)
    out = result.stdout.strip()
    return out

def process_one(rel):
    """Process one article: read, translate, write"""
    eng_path = os.path.join(WORKDIR, rel, "index.html")
    zh_path = os.path.join(WORKDIR, "zh", rel, "index.html")
    
    print(f"\n{'='*60}")
    print(f"[{missing.index(rel)+1}/{len(missing)}] {rel}")
    print(f"{'='*60}")
    
    with open(eng_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    meta = extract_en(html, rel)
    print(f"  EN: {meta['en_title']}")
    print(f"  Body: {len(meta['en_body'])} chars")
    
    # Translate metadata
    print("  → Translating metadata...")
    zh = translate_meta(meta['en_title'], meta['en_desc'], meta['en_h1'], meta['en_type'])
    time.sleep(0.5)
    
    # Translate body
    print("  → Translating body...")
    zh_body = translate_body(meta['en_body'], f"{meta['en_title']} | {rel}")
    
    # Clean body
    zh_body = zh_body.replace('<!--NEWSLETTER_SECTION-->', '').replace('<!--FAQ_SCHEMA_ZH-->', '')
    # Remove newsletter form if present
    zh_body = re.sub(r'<div class="container"><div class="newsletter-box">.*?</div></div>\s*', '', zh_body, flags=re.DOTALL)
    
    # Assemble
    output = TEMPLATE.format(
        TITLE=zh.get('zh_title', meta['en_title']),
        DESC=zh.get('zh_desc', meta['en_desc']),
        CANON=meta['canon'],
        OGTITLE=zh.get('zh_title', meta['en_title']),
        OGDESC=zh.get('zh_desc', meta['en_desc']),
        H1=zh.get('zh_h1', meta['en_h1']),
        TYPE=zh.get('zh_type', meta['en_type']),
        READTIME=meta['readtime'],
        BODY=zh_body
    )
    
    os.makedirs(os.path.dirname(zh_path), exist_ok=True)
    with open(zh_path, 'w', encoding='utf-8') as f:
        f.write(output)
    
    print(f"  ✓ Wrote: zh/{rel}/index.html")
    return True

if __name__ == '__main__':
    missing = find_missing()
    print(f"Found {len(missing)} missing Chinese articles\n")
    
    for i, rel in enumerate(missing):
        try:
            process_one(rel)
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
            # Continue with next
    
    print(f"\n{'='*60}")
    print("Done!")
