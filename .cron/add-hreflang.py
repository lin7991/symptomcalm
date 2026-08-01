#!/usr/bin/env python3
"""Add bidirectional hreflang tags to EN + ZH pages."""
import os, re
from pathlib import Path

WORK = Path(os.path.expanduser("~/symptomcalm"))

def add_hreflang(filepath):
    """Add hreflang alternate links to both EN and ZH versions."""
    with open(filepath) as f:
        html = f.read()
    
    rel = filepath.relative_to(WORK)
    parts = list(rel.parts)
    is_zh = parts[0] == 'zh'
    
    if is_zh:
        # ZH page → add hreflang en (already has it usually)
        en_path = '/'.join(parts[1:])
        en_url = f"https://symptomcalm.com/{en_path}"
        zh_url = f"https://symptomcalm.com/{'/'.join(parts)}"
        # Ensure hreflang en + zh + x-default exist
        if 'hreflang="en"' not in html:
            html = html.replace('</head>', f'  <link rel="alternate" hreflang="en" href="{en_url}" />\n</head>')
        if 'hreflang="x-default"' not in html:
            html = html.replace('</head>', f'  <link rel="alternate" hreflang="x-default" href="{en_url}" />\n</head>')
    else:
        # EN page → add hreflang zh
        en_url = f"https://symptomcalm.com/{'/'.join(parts)}"
        zh_url = f"https://symptomcalm.com/zh/{'/'.join(parts)}"
        # Check if ZH version exists
        zh_path = WORK / 'zh' / Path('/'.join(parts))
        zh_exists = zh_path.exists()
        
        if 'hreflang="zh"' not in html:
            if zh_exists:
                html = html.replace('</head>', f'  <link rel="alternate" hreflang="zh" href="{zh_url}" />\n</head>')
        if 'hreflang="x-default"' not in html:
            html = html.replace('</head>', f'  <link rel="alternate" hreflang="x-default" href="{en_url}" />\n</head>')
    
    with open(filepath, 'w') as f:
        f.write(html)
    return True

def main():
    count = 0
    for f in sorted(WORK.rglob('index.html')):
        rel = f.relative_to(WORK)
        if '.git/' in str(rel) or 'node_modules/' in str(rel) or '.cron/' in str(rel):
            continue
        add_hreflang(f)
        count += 1
    
    print(f"✅ Added hreflang to {count} pages")

if __name__ == "__main__":
    main()
