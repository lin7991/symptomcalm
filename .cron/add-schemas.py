#!/usr/bin/env python3
"""Add BreadcrumbList + Article Schema to all HTML pages."""
import json, os, re
from pathlib import Path

WORK = Path(os.path.expanduser("~/symptomcalm"))
EN_SITE_NAME = "SymptomCalm"
ZH_SITE_NAME = "SymptomCalm"

# Breadcrumb name mappings (EN → ZH)
EN_NAMES = {
    "symptoms": "Symptoms", "anxiety": "Anxiety", "back-pain": "Back Pain",
    "insomnia": "Insomnia", "digestion": "Digestion", "headaches": "Headaches",
    "fatigue": "Fatigue", "allergies": "Allergies", "skin-conditions": "Skin Conditions",
    "womens-health": "Women's Health", "joint-pain": "Joint Pain", "stress": "Stress",
    "respiratory-health": "Respiratory Health", "mental-emotional-health": "Mental & Emotional Health",
    "tcm-basics": "TCM Basics", "treatments": "Treatments", "about": "About",
    "contact": "Contact", "eye-health": "Eye Health", "ear-health-tinnitus": "Ear Health & Tinnitus",
}
ZH_NAMES = {
    "symptoms": "症状", "anxiety": "焦虑", "back-pain": "背痛",
    "insomnia": "失眠", "digestion": "消化", "headaches": "头痛",
    "fatigue": "疲劳", "allergies": "过敏", "skin-conditions": "皮肤",
    "womens-health": "女性健康", "joint-pain": "关节", "stress": "压力",
    "respiratory-health": "呼吸健康", "mental-emotional-health": "心理与情绪",
    "tcm-basics": "中医基础", "treatments": "疗法", "about": "关于",
    "contact": "联系我们", "eye-health": "眼部健康", "ear-health-tinnitus": "耳鸣",
}

def build_breadcrumb(path_parts, is_zh):
    """Build BreadcrumbList items."""
    names = ZH_NAMES if is_zh else EN_NAMES
    items = []
    url_prefix = "/zh" if is_zh else ""
    
    # Home
    home_name = "首页" if is_zh else "Home"
    items.append({"@type": "ListItem", "position": 1, "name": home_name, "item": f"https://symptomcalm.com{url_prefix}/"})
    
    pos = 2
    current = ""
    for part in path_parts:
        if part in ('index.html', 'zh'): 
            continue
        current += f"/{part}"
        display = names.get(part, part.replace('-', ' ').title())
        items.append({"@type": "ListItem", "position": pos, "name": display, "item": f"https://symptomcalm.com{url_prefix}{current}/"})
        pos += 1
    
    return items

def add_schemas(filepath):
    """Add BreadcrumbList and Article schema to an HTML file."""
    with open(filepath) as f:
        html = f.read()
    
    # Skip if already has BreadcrumbList
    if '"BreadcrumbList"' in html:
        return False
    
    rel_path = filepath.relative_to(WORK)
    parts = list(rel_path.parts)
    is_zh = parts[0] == 'zh'
    
    # Get title
    title_match = re.search(r'<title>(.*?)</title>', html)
    title = title_match.group(1) if title_match else "SymptomCalm"
    
    # Get description
    desc_match = re.search(r'<meta name="description" content="([^"]*)"', html)
    description = desc_match.group(1) if desc_match else ""
    
    # Get path parts for breadcrumb
    path_parts = list(rel_path.parent.parts) if rel_path.name == 'index.html' else list(rel_path.parts[:-1])
    
    # Build BreadcrumbList
    breadcrumb_items = build_breadcrumb(path_parts, is_zh)
    
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "BreadcrumbList",
                "itemListElement": breadcrumb_items
            },
            {
                "@type": "Article",
                "headline": title,
                "description": description,
                "author": {"@type": "Person", "name": "Xiao Lin"},
                "publisher": {"@type": "Organization", "name": "SymptomCalm", "url": "https://symptomcalm.com"},
                "datePublished": "2026-06-01",
                "dateModified": "2026-07-15"
            }
        ]
    }
    
    schema_html = f'  <script type="application/ld+json">\n{json.dumps(schema, indent=2, ensure_ascii=False)}\n  </script>\n'
    
    # Insert before </head>
    # Remove existing schemas first
    html = re.sub(r'\s*<script type="application/ld\+json">.*?</script>', '', html, flags=re.DOTALL)
    html = html.replace('</head>', f'{schema_html}</head>')
    
    with open(filepath, 'w') as f:
        f.write(html)
    
    return True

def main():
    count = 0
    for f in sorted(WORK.rglob('index.html')):
        rel = f.relative_to(WORK)
        if '.git/' in str(rel) or 'node_modules/' in str(rel) or '.cron/' in str(rel):
            continue
        if add_schemas(f):
            count += 1
            if count % 50 == 0:
                print(f"  {count}...")
    
    print(f"✅ Updated {count} pages with BreadcrumbList + Article schema")

if __name__ == "__main__":
    main()
