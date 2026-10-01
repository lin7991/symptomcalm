#!/usr/bin/env python3
"""Release gate for SymptomCalm pages. Exits non-zero on blocking quality/SEO defects."""
import re, sys
from pathlib import Path
from html import unescape

ROOT = Path(__file__).resolve().parents[1]
BANNED = re.compile(r'\b(?:cure|heals?|healing|treats?|treatment for|prevents?|prevent)\b', re.I)
REQUIRED_EN = ('Disclaimer', 'When to See a Doctor', 'Research', 'Practical Takeaways')

def strip_html(s): return re.sub(r'<script.*?</script>|<style.*?</style>|<[^>]+>', ' ', s, flags=re.I|re.S)

def main():
    errors=[]; warnings=[]; pages=0; articles=0
    files=sorted(ROOT.rglob('index.html'))
    for f in files:
        if any(x in f.parts for x in ('.git','node_modules','.cron')): continue
        pages += 1
        text=f.read_text(encoding='utf-8',errors='replace')
        rel=f.relative_to(ROOT).as_posix()
        for marker,label in [(r'<link[^>]+rel="canonical"', 'canonical'),(r'property="og:title"','og:title'),(r'property="og:description"','og:description'),(r'property="og:image"','og:image'),(r'hreflang="x-default"','x-default'),(r'"@type": "Organization"','Organization'),(r'"@type": "MedicalWebPage"','MedicalWebPage'),(r'dateModified','dateModified')]:
            if not re.search(marker,text,re.I): errors.append(f'{rel}: missing {label}')
        is_en_article = (not rel.startswith('zh/') and rel.startswith(('symptoms/','treatments/','tcm-basics/')) and len(f.relative_to(ROOT).parts) >= 4)
        if is_en_article:
            articles += 1
            body=strip_html(text)
            words=re.findall(r"\b[A-Za-z][A-Za-z'-]*\b",body)
            if len(words)<600: warnings.append(f'{rel}: only {len(words)} English words')
            section_variants = {
                'doctor': (r'when to see (a )?doctor', r'seek medical attention', r'when to seek help', r'safety'),
                'research': (r'\bresearch\b', r'evidence', r'what studies say', r'what science says'),
                'takeaways': (r'practical takeaways', r'key takeaways', r'what to remember', r'next steps', r'practical steps'),
            }
            for label, variants in section_variants.items():
                if not any(re.search(v, body, re.I) for v in variants): warnings.append(f'{rel}: missing {label} section')
            claims=[x.group(0) for x in BANNED.finditer(body) if 'not' not in body[max(0,x.start()-35):x.start()].lower()]
            if len(claims)>8: warnings.append(f'{rel}: review medical claim wording ({len(claims)} hits)')
        if rel.startswith('zh/') and '/symptoms/' in rel:
            if '免责声明' not in text: errors.append(f'{rel}: missing Chinese disclaimer')
    print(f'PAGES={pages} EN_ARTICLES={articles} ERRORS={len(errors)} WARNINGS={len(warnings)}')
    for x in errors[:80]: print('ERROR',x)
    for x in warnings[:30]: print('WARN',x)
    return 1 if errors else 0

if __name__=='__main__': sys.exit(main())
