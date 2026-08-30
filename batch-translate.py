#!/usr/bin/env python3
"""
Batch translate English articles to Chinese using Hermes CLI.
"""
import os, re, subprocess, sys, json, time, html

WORKDIR = "/Users/xj/symptomcalm"

# Template (with placeholders)
TEMPLATE_HEAD = '''<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{TITLE_ZH} — SymptomCalm</title>
  <meta name="description" content="{META_DESC_ZH}" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Serif+SC:wght@400;600;700&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="/styles/style.css" />
  <link rel="canonical" href="https://symptomcalm.com/zh{CANONICAL_PATH}/" />
  <link rel="alternate" hreflang="en" href="https://symptomcalm.com{CANONICAL_PATH}/" />
  <meta property="og:title" content="{OG_TITLE_ZH}" />
  <meta property="og:description" content="{OG_DESC_ZH}" />
  <meta property="og:url" content="https://symptomcalm.com/zh{CANONICAL_PATH}/" />
  <meta property="og:type" content="website" />
  <meta property="og:image" content="https://symptomcalm.com/favicon.svg" />
  <meta name="twitter:card" content="summary_large_image" />
  <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": "SymptomCalm",
    "url": "https://symptomcalm.com/zh{CANONICAL_PATH}/"
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
    <h1>{H1_ZH}</h1>
    <div class="meta">{TYPE_LABEL_ZH} · {READ_TIME} 分钟阅读</div>
  </div>

  <div class="article-body">

{CONTENT_ZH}

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

# Find all missing files
def find_missing():
    missing = []
    for root_dir in ["symptoms", "tcm-basics", "treatments"]:
        for dirpath, dirnames, filenames in os.walk(os.path.join(WORKDIR, root_dir)):
            if "index.html" not in filenames:
                continue
            rel_path = os.path.relpath(dirpath, WORKDIR)
            zh_path = os.path.join(WORKDIR, "zh", rel_path, "index.html")
            if not os.path.exists(zh_path):
                missing.append(rel_path)
    return sorted(missing)

def extract_meta(html_content, rel_path):
    """Extract metadata from English article"""
    # Title
    title_match = re.search(r'<title>(.*?) — SymptomCalm</title>', html_content)
    en_title = title_match.group(1) if title_match else ""
    
    # Meta description
    desc_match = re.search(r'<meta name="description" content="(.*?)"', html_content)
    en_desc = desc_match.group(1) if desc_match else ""
    
    # H1
    h1_match = re.search(r'<h1>(.*?)</h1>', html_content)
    en_h1 = h1_match.group(1) if h1_match else ""
    
    # Meta (read time + type)
    meta_match = re.search(r'<div class="meta">(.*?) · (\d+) min read</div>', html_content)
    if meta_match:
        en_type_label = meta_match.group(1)
        read_time = meta_match.group(2)
    else:
        en_type_label = ""
        read_time = "8"
    
    # Canonical path
    canon_match = re.search(r'<link rel="canonical" href="https://symptomcalm\.com(/.*?)/"', html_content)
    canonical_path = canon_match.group(1) if canon_match else "/" + rel_path
    
    # Extract article body HTML
    body_match = re.search(r'<div class="article-body">(.*?)</div>\s*\n\s*</article>', html_content, re.DOTALL)
    if not body_match:
        body_match = re.search(r'<div class="article-body">(.*?)</div>', html_content, re.DOTALL)
    en_body = body_match.group(1).strip() if body_match else ""
    
    return {
        "en_title": en_title,
        "en_desc": en_desc,
        "en_h1": en_h1,
        "en_type_label": en_type_label,
        "read_time": read_time,
        "canonical_path": canonical_path,
        "en_body": en_body,
    }

def translate_with_hermes(text, context):
    """Use hermes CLI to translate text"""
    prompt = f"""You are a medical translator specializing in Traditional Chinese Medicine (TCM) content. 
Translate the following TCM article content from English to Chinese (Simplified).

Keep ALL HTML tags, structure, and formatting exactly as-is. Only translate the text content between/inside tags.
Preserve all links (href values), class names, and HTML attributes unchanged.
Keep English terms like "Qi", "Yin", "Yang", "Spleen", "Kidney", "Liver", "Lung" in English (they're standard TCM terms even in Chinese text).
Make sure Chinese reads naturally - use proper medical terminology.
DO NOT translate: URLs, href values, code-like content, measurement units.

Context (article type, category): {context}

TEXT TO TRANSLATE:
{text}

Return ONLY the translated HTML text, nothing else."""
    
    result = subprocess.run(
        ["hermes", "-p", "symptomcalm", "ask", prompt],
        capture_output=True, text=True, timeout=120,
        cwd=WORKDIR
    )
    output = result.stdout.strip()
    if not output:
        output = result.stderr.strip()
    return output

def translate_meta_with_hermes(en_title, en_desc, en_h1, en_type_label):
    """Translate just the metadata fields"""
    prompt = f"""Translate the following TCM article metadata from English to Chinese (Simplified).
Return a JSON object with keys: zh_title, zh_desc, zh_h1, zh_type_label

English title: {en_title}
English description: {en_desc}
English H1 heading: {en_h1}
English type label: {en_type_label}

Important:
- Keep "Qi", "Yin", "Yang" in English
- Make titles concise and natural in Chinese
- Description should be a complete, compelling Chinese sentence
- Type label should be a short Chinese phrase like "综合指南" or "症状指南"
- Return ONLY valid JSON, no other text"""
    
    result = subprocess.run(
        ["hermes", "-p", "symptomcalm", "ask", prompt],
        capture_output=True, text=True, timeout=60,
        cwd=WORKDIR
    )
    output = result.stdout.strip()
    if not output:
        output = result.stderr.strip()
    
    # Try to extract JSON from the output
    json_match = re.search(r'\{[^{}]*"zh_title"[^{}]*\}', output, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except:
            pass
    
    # Fallback
    return {
        "zh_title": en_title,
        "zh_desc": en_desc,
        "zh_h1": en_h1,
        "zh_type_label": en_type_label
    }

def process_article(rel_path):
    """Process one article: read English, translate, write Chinese"""
    eng_path = os.path.join(WORKDIR, rel_path, "index.html")
    zh_path = os.path.join(WORKDIR, "zh", rel_path, "index.html")
    
    print(f"\n{'='*60}")
    print(f"Processing: {rel_path}")
    print(f"{'='*60}")
    
    # Read English file
    with open(eng_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    meta = extract_meta(html_content, rel_path)
    
    print(f"  Title: {meta['en_title']}")
    print(f"  Read time: {meta['read_time']} min")
    print(f"  Body length: {len(meta['en_body'])} chars")
    
    # Translate metadata
    print("  Translating metadata...")
    zh_meta = translate_meta_with_hermes(
        meta['en_title'], meta['en_desc'], 
        meta['en_h1'], meta['en_type_label']
    )
    zh_title = zh_meta.get('zh_title', meta['en_title'])
    zh_desc = zh_meta.get('zh_desc', meta['en_desc'])
    zh_h1 = zh_meta.get('zh_h1', meta['en_h1'])
    zh_type_label = zh_meta.get('zh_type_label', meta['en_type_label'])
    
    print(f"  ZH Title: {zh_title}")
    
    # Translate body
    print("  Translating body content...")
    context = f"Article: {meta['en_title']}, Category: {rel_path.split('/')[0]}"
    zh_body = translate_with_hermes(meta['en_body'], context)
    
    # Clean up body - remove any FAQ schema if present
    zh_body = re.sub(r'<!--NEWSLETTER_SECTION-->', '', zh_body)
    zh_body = re.sub(r'<!--FAQ_SCHEMA_ZH-->', '', zh_body)
    
    # Generate OG title (same as zh_title for simplicity)
    og_title_zh = zh_title
    og_desc_zh = zh_desc
    
    # Fill template
    output = TEMPLATE_HEAD.format(
        TITLE_ZH=zh_title,
        META_DESC_ZH=zh_desc,
        CANONICAL_PATH=meta['canonical_path'],
        OG_TITLE_ZH=og_title_zh,
        OG_DESC_ZH=og_desc_zh,
        H1_ZH=zh_h1,
        TYPE_LABEL_ZH=zh_type_label,
        READ_TIME=meta['read_time'],
        CONTENT_ZH=zh_body,
    )
    
    # Write
    os.makedirs(os.path.dirname(zh_path), exist_ok=True)
    with open(zh_path, 'w', encoding='utf-8') as f:
        f.write(output)
    
    print(f"  ✓ Wrote: {zh_path}")
    return True

def main():
    missing = find_missing()
    total = len(missing)
    print(f"Found {total} missing Chinese articles")
    
    success = 0
    failures = 0
    
    for i, rel_path in enumerate(missing, 1):
        print(f"\n[{i}/{total}] ", end="")
        try:
            if process_article(rel_path):
                success += 1
                time.sleep(1)  # Rate limiting
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
            failures += 1
            # Save error info for retry
            with open("/Users/xj/symptomcalm/translate_errors.log", "a") as f:
                f.write(f"{rel_path}: {e}\n")
    
    print(f"\n{'='*60}")
    print(f"Done! {success}/{total} articles translated successfully")
    print(f"Failures: {failures}")
    
    # Show failures
    if failures > 0:
        with open("/Users/xj/symptomcalm/translate_errors.log", "r") as f:
            print("\nFailed articles:")
            print(f.read())

if __name__ == "__main__":
    main()
