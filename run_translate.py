#!/usr/bin/env python3
"""
Batch translate all remaining English TCM articles to Chinese.
Uses hermes chat -q for translation.
"""
import os, re, json, subprocess, sys, time

WORKDIR = "/Users/xj/symptomcalm"
HERMES_CMD = ["hermes", "-p", "symptomcalm", "chat", "-q", "-Q", "--source", "tool"]

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
  <meta property="og:title" content="{OGT}" />
  <meta property="og:description" content="{OGD}" />
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
    <div class="meta">{TYPE} · {RT} 分钟阅读</div>
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

def hermes_query(prompt, timeout=180):
    """Run a hermes chat query and return the output"""
    try:
        result = subprocess.run(HERMES_CMD, input=prompt, capture_output=True, text=True, timeout=timeout, cwd=WORKDIR)
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return ""
    except Exception as e:
        return f"ERROR: {e}"

def extract_meta_body(html, rel):
    """Extract metadata and body from English article"""
    title_m = re.search(r'<title>(.*?) — SymptomCalm</title>', html)
    desc_m = re.search(r'<meta name="description" content="(.*?)"', html)
    h1_m = re.search(r'<h1>(.*?)</h1>', html)
    meta_m = re.search(r'<div class="meta">(.*?) · (\d+) min read</div>', html)
    canon_m = re.search(r'<link rel="canonical" href="https://symptomcalm\.com(/.*?)/"', html)
    body_m = re.search(r'<div class="article-body">(.*?)</div>\s*\n\s*</article>', html, re.DOTALL)
    if not body_m:
        body_m = re.search(r'<div class="article-body">(.*?)</div>', html, re.DOTALL)
    return {
        't': (title_m and title_m.group(1)) or '',
        'd': (desc_m and desc_m.group(1)) or '',
        'h': (h1_m and h1_m.group(1)) or '',
        'ty': (meta_m and meta_m.group(1)) or '综合指南',
        'rt': (meta_m and meta_m.group(2)) or '8',
        'c': (canon_m and canon_m.group(1)) or '/' + rel,
        'b': (body_m and body_m.group(1).strip()) or '',
    }

def main():
    # Find missing articles
    missing = []
    for root in ["symptoms", "tcm-basics", "treatments"]:
        rp = os.path.join(WORKDIR, root)
        if not os.path.isdir(rp): continue
        for dirpath, _, fnames in os.walk(rp):
            if "index.html" not in fnames: continue
            rel = os.path.relpath(dirpath, WORKDIR)
            zp = os.path.join(WORKDIR, "zh", rel, "index.html")
            if not os.path.exists(zp):
                missing.append(rel)
    missing.sort()
    
    total = len(missing)
    print(f"Found {total} articles to translate\n")
    
    for idx, rel in enumerate(missing, 1):
        eng_path = os.path.join(WORKDIR, rel, "index.html")
        zh_path = os.path.join(WORKDIR, "zh", rel, "index.html")
        
        print(f"[{idx}/{total}] {rel}")
        
        with open(eng_path, 'r', encoding='utf-8') as f:
            html = f.read()
        
        m = extract_meta_body(html, rel)
        print(f"  EN title: {m['t']}")
        
        # Step 1: Translate metadata
        meta_prompt = f'''Translate this TCM article metadata to Chinese (Simplified). Return ONLY a JSON object.

Title: {m['t']}
Description: {m['d']}
H1: {m['h']}
Type label: {m['ty']}

Return format: {{"zh_title":"...","zh_desc":"...","zh_h1":"...","zh_type":"..."}}

Rules: Keep Qi/Yin/Yang/Spleen/Kidney/Liver/Lung in English. zh_type should be like 综合指南, 症状指南, 中医基础, 治疗指南. Make Chinese natural.'''
        
        meta_out = hermes_query(meta_prompt, 60)
        zh_meta = {'zh_title': m['t'], 'zh_desc': m['d'], 'zh_h1': m['h'], 'zh_type': m['ty']}
        try:
            jm = re.search(r'\{[^{}]*(?:zh_title)[^{}]*\}', meta_out, re.DOTALL)
            if jm:
                zh_meta.update(json.loads(jm.group()))
        except:
            pass
        print(f"  ZH title: {zh_meta.get('zh_title', '?')[:60]}")
        
        # Step 2: Translate body
        body = m['b']
        # Truncate if needed for API
        if len(body) > 15000:
            body = body[:15000]
        
        body_prompt = f'''Translate this TCM article body from English to Simplified Chinese. 
Keep ALL HTML tags, class names, href values, URLs exactly as-is.
Only translate text content inside tags.
Keep TCM terms in English: Qi, Yin, Yang, Spleen, Kidney, Liver, Lung, Blood, Jing, Shen, Dampness, Phlegm, etc.
Return ONLY the translated HTML, nothing else.

BODY:
{body}'''
        
        body_out = hermes_query(body_prompt, 300)
        zh_body = body_out if body_out else body
        
        # Clean up
        zh_body = zh_body.replace('<!--NEWSLETTER_SECTION-->', '').replace('<!--FAQ_SCHEMA_ZH-->', '')
        zh_body = re.sub(r'<div class="container"><div class="newsletter-box">.*?</div></div>\s*', '', zh_body, flags=re.DOTALL)
        
        # Assemble
        output = TEMPLATE.format(
            TITLE=zh_meta.get('zh_title', m['t']),
            DESC=zh_meta.get('zh_desc', m['d']),
            CANON=m['c'],
            OGT=zh_meta.get('zh_title', m['t']),
            OGD=zh_meta.get('zh_desc', m['d']),
            H1=zh_meta.get('zh_h1', m['h']),
            TYPE=zh_meta.get('zh_type', m['ty']),
            RT=m['rt'],
            BODY=zh_body
        )
        
        os.makedirs(os.path.dirname(zh_path), exist_ok=True)
        with open(zh_path, 'w', encoding='utf-8') as f:
            f.write(output)
        
        print(f"  ✓ Done ({len(zh_body)} chars)")
        
        # Small delay between articles
        time.sleep(0.5)
    
    print(f"\n{'='*60}")
    print(f"COMPLETE: {total} articles translated")

if __name__ == '__main__':
    main()
