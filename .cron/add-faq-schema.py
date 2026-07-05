#!/usr/bin/env python3
"""
Add FAQPage Schema to all content articles.
Extracts H2 headings (main questions/topics) and generates JSON-LD FAQ schema.
"""
import json, os, re, sys
from pathlib import Path

WORKDIR = Path(os.path.expanduser("~/symptomcalm"))

# Skip these pages (legal/info pages - no FAQ needed)
SKIP_PATTERNS = [
    "/about/", "/contact/", "/privacy", "/disclaimer", "/legal",
]

# Content pages to process (all article pages)
CONTENT_DIRS = [
    "symptoms/anxiety", "symptoms/back-pain", "symptoms/insomnia",
    "symptoms/digestion", "symptoms/headaches", "symptoms/fatigue",
    "symptoms/allergies", "symptoms/skin-conditions", "symptoms/womens-health",
    "symptoms/joint-pain", "symptoms/mental-emotional-health",
    "symptoms/respiratory-health", "symptoms/stress",
    "tcm-basics",
    "treatments",
]


def extract_headings(html):
    """Extract H2 headings from article body (skip disclaimer, CTA sections)."""
    # Find the article-body section
    body_match = re.search(r'<div class="article-body">(.*?)</div>\s*</article>', html, re.DOTALL)
    if not body_match:
        return []
    
    body = body_match.group(1)
    
    # Extract H2 text content
    headings = re.findall(r'<h2>(.*?)</h2>', body, re.DOTALL)
    
    # Clean HTML tags from heading text
    clean = []
    for h in headings:
        text = re.sub(r'<[^>]+>', '', h).strip()
        # Skip if too short (< 10 chars) or contains common non-question headings
        if len(text) < 10:
            continue
        if any(skip in text.lower() for skip in ["practical takeaway", "when to see", "coming soon", "continue exploring", "what research says"]):
            continue
        clean.append(text)
    
    return clean[:5]  # Max 5 FAQ items (Google best practice)


def heading_to_answer(heading, title):
    """Generate a natural answer based on the heading and article context."""
    # If heading ends with ?, treat as question
    if heading.endswith("?"):
        return f"This section of our article on {title} addresses this question in detail, exploring the TCM perspective and practical implications."
    
    # Otherwise create a question-style FAQ entry
    return f"In TCM theory, {heading.lower()} — our article explores this concept and its relevance to your health."


def add_faq_schema(filepath):
    """Add FAQPage JSON-LD schema to an HTML file."""
    with open(filepath) as f:
        html = f.read()
    
    # Get the title for context
    title_match = re.search(r'<title>(.*?)</title>', html)
    title = title_match.group(1) if title_match else "SymptomCalm"
    
    # Extract headings
    headings = extract_headings(html)
    if len(headings) < 2:
        return None  # Not enough headings for meaningful FAQ
    
    # Generate FAQ entries
    questions = []
    for h in headings:
        questions.append({
            "@type": "Question",
            "name": h,
            "acceptedAnswer": {
                "@type": "Answer",
                "text": heading_to_answer(h, title)
            }
        })
    
    schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": questions
    }
    
    schema_html = f'  <script type="application/ld+json">\n{json.dumps(schema, indent=2, ensure_ascii=False)}\n  </script>\n'
    
    # Insert before </head>
    if '</head>' in html:
        # Remove existing FAQ schema if present
        html = re.sub(r'\s*<script type="application/ld\+json">.*?"@type":\s*"FAQPage".*?</script>', '', html, flags=re.DOTALL)
        
        html = html.replace('</head>', f'{schema_html}</head>')
        
        with open(filepath, 'w') as f:
            f.write(html)
        
        return len(questions)
    
    return None


def main():
    count = 0
    total_q = 0
    skipped = []
    
    for content_dir in CONTENT_DIRS:
        dirpath = WORKDIR / content_dir
        if not dirpath.exists():
            continue
        
        # Walk all index.html files in subdirectories
        for root, dirs, files in os.walk(dirpath):
            for f in files:
                if f != "index.html":
                    continue
                filepath = Path(root) / f
                rel_path = str(filepath.relative_to(WORKDIR))
                
                q_count = add_faq_schema(filepath)
                if q_count:
                    count += 1
                    total_q += q_count
                    print(f"  ✅ {rel_path} ({q_count} FAQ)")
                else:
                    skipped.append(rel_path)
    
    print(f"\nTotal: {count} pages updated, {total_q} FAQ items added")
    if skipped:
        print(f"Skipped (no headings or insufficient): {len(skipped)} pages")
    
    return count > 0


if __name__ == "__main__":
    main()
