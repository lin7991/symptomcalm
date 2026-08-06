#!/usr/bin/env python3
"""Add og:image, share buttons, and related articles to all article pages."""
import os, re
from pathlib import Path

WORK = Path(os.path.expanduser("~/symptomcalm"))

# Category mapping for images
CAT_IMAGES = {
    "anxiety": "anxiety.svg", "back-pain": "back-pain.svg", "insomnia": "insomnia.svg",
    "digestion": "digestion.svg", "headaches": "headaches.svg", "fatigue": "fatigue.svg",
    "allergies": "allergies.svg", "skin-conditions": "skin-conditions.svg",
    "womens-health": "womens-health.svg", "joint-pain": "joint-pain.svg",
    "stress": "stress.svg", "respiratory-health": "respiratory-health.svg",
    "mental-emotional-health": "mental-emotional-health.svg",
    "tcm-basics": "tcm-basics.svg", "treatments": "treatments.svg",
    "eye-health": "eye-health.svg", "ear-health-tinnitus": "ear-health-tinnitus.svg",
}

SHARE_BUTTONS = '''<div class="share-section" style="margin:2.5rem 0;padding:1.5rem;background:var(--bg-alt);border-radius:var(--radius-lg);text-align:center;">
  <p style="font-weight:600;margin-bottom:1rem;color:var(--text);">💬 Found this helpful? Share it:</p>
  <div style="display:flex;gap:0.75rem;justify-content:center;flex-wrap:wrap;">
    <a href="https://twitter.com/intent/tweet?text={{TITLE_ENC}}&url={{URL_ENC}}" target="_blank" rel="noopener" style="display:inline-block;background:#1DA1F2;color:white;padding:0.5rem 1.25rem;border-radius:6px;font-size:0.85rem;font-weight:600;text-decoration:none;">𝕏 Twitter</a>
    <a href="https://www.facebook.com/sharer/sharer.php?u={{URL_ENC}}" target="_blank" rel="noopener" style="display:inline-block;background:#1877F2;color:white;padding:0.5rem 1.25rem;border-radius:6px;font-size:0.85rem;font-weight:600;text-decoration:none;">f Facebook</a>
    <a href="https://www.linkedin.com/sharing/share-offsite/?url={{URL_ENC}}" target="_blank" rel="noopener" style="display:inline-block;background:#0A66C2;color:white;padding:0.5rem 1.25rem;border-radius:6px;font-size:0.85rem;font-weight:600;text-decoration:none;">in LinkedIn</a>
    <a href="https://pinterest.com/pin/create/button/?url={{URL_ENC}}&media={{IMG_ENC}}&description={{TITLE_ENC}}" target="_blank" rel="noopener" style="display:inline-block;background:#E60023;color:white;padding:0.5rem 1.25rem;border-radius:6px;font-size:0.85rem;font-weight:600;text-decoration:none;">📌 Pinterest</a>
    <a href="mailto:?subject={{TITLE_ENC}}&body={{URL_ENC}}" style="display:inline-block;background:#718096;color:white;padding:0.5rem 1.25rem;border-radius:6px;font-size:0.85rem;font-weight:600;text-decoration:none;">✉️ Email</a>
  </div>
</div>'''

def get_category(path_str):
    """Determine category from path."""
    for cat in CAT_IMAGES:
        if f"/{cat}/" in path_str:
            return cat
    return "tcm-basics"

def get_related_articles(html, path_str, title):
    """Find related articles from pillar page links."""
    return None  # Placeholder - could implement later

def process_file(filepath):
    with open(filepath) as f:
        html = f.read()
    
    rel = filepath.relative_to(WORK)
    rel_str = str(rel)
    is_zh = rel_str.startswith('zh/')
    
    # Skip legal/info pages
    if rel_str.startswith('about/') or rel_str.startswith('contact/') or 'privacy' in rel_str or 'disclaimer' in rel_str:
        return False
    
    # Get category
    cat = get_category(rel_str)
    img_file = CAT_IMAGES.get(cat, "default.svg")
    img_url = f"https://symptomcalm.com/images/{img_file}"
    
    # Determine canonical URL
    if is_zh:
        en_part = rel_str.replace('zh/', '', 1)
        canon = f"https://symptomcalm.com/zh/{en_part}"
    else:
        canon = f"https://symptomcalm.com/{rel_str}"
    
    # Update og:image
    html = re.sub(r'<meta property="og:image" content="[^"]*"', f'<meta property="og:image" content="{img_url}"', html)
    # Add twitter:image if missing
    if 'twitter:image' not in html:
        html = html.replace('</head>', f'  <meta name="twitter:image" content="{img_url}" />\n</head>')
    
    # Skip share buttons + related for homepage
    if rel_str in ('index.html', 'zh/index.html'):
        with open(filepath, 'w') as f:
            f.write(html)
        return True
    
    # Get title for share buttons
    title_match = re.search(r'<title>(.*?)</title>', html)
    title = title_match.group(1) if title_match else "SymptomCalm"
    
    # Add share buttons before footer (skip if already has)
    if 'share-section' not in html:
        url_enc = canon
        title_enc = title
        share_html = SHARE_BUTTONS
        share_html = share_html.replace("{{URL_ENC}}", url_enc)
        share_html = share_html.replace("{{TITLE_ENC}}", title_enc)
        share_html = share_html.replace("{{IMG_ENC}}", img_url)
        html = html.replace('<footer class="site-footer">', f'{share_html}\n\n<footer class="site-footer">')
    
    with open(filepath, 'w') as f:
        f.write(html)
    return True

def main():
    count = 0
    for f in sorted(WORK.rglob('index.html')):
        rel = f.relative_to(WORK)
        if '.git/' in str(rel) or 'node_modules/' in str(rel) or '.cron/' in str(rel):
            continue
        if process_file(f):
            count += 1
    print(f"✅ Updated {count} pages (og:image + share buttons)")

if __name__ == "__main__":
    main()
