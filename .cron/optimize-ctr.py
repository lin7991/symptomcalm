#!/usr/bin/env python3
"""Batch optimize meta descriptions + titles for better Google CTR."""
import os, re, json
from pathlib import Path

WORK = Path(os.path.expanduser("~/symptomcalm"))

# Skip these (legal/info pages - keep original)
SKIP_DIRS = ['about/', 'contact/', '.git', 'node_modules', '.cron']

# Title optimization patterns per type
def optimize_title(en_title, path):
    """Add brackets/numbers to title for higher CTR."""
    title = en_title.split('—')[0].strip() if '—' in en_title else en_title
    
    # Already has brackets? skip
    if '[' in title or ']' in title:
        return en_title
    
    path_str = str(path)
    
    # Pillar pages
    if len(path.parents) <= 2 and 'symptoms/' in path_str:
        brackets = {
            'anxiety': '[4 Patterns & Remedies]',
            'back-pain': '[Causes & TCM Solutions]',
            'insomnia': '[4 Patterns & Sleep Tips]',
            'digestion': '[Spleen Qi & Diet Guide]',
            'headaches': '[Types & TCM Relief]',
            'fatigue': '[Qi & Blood Deficiency]',
            'allergies': '[Wei Qi & Natural Relief]',
            'skin-conditions': '[Blood Heat & Dampness]',
            'womens-health': '[Hormones & Organ Health]',
            'joint-pain': '[Bi Syndrome & Herbs]',
            'stress': '[Shen & Organ Balance]',
            'respiratory-health': '[Lung Qi & Immunity]',
            'eye-health': '[Liver Blood & Vision]',
        }
        for key, bracket in brackets.items():
            if key in path_str:
                return f"{title} {bracket}"
    
    # TCM Basics
    if 'tcm-basics/' in path_str:
        return f"{title} [Beginner's Guide 2026]"
    
    # Treatments
    if 'treatments/' in path_str:
        return f"{title} [What Science Says]"
    
    # Cluster articles
    if len(path.parents) >= 3:
        return f"{title} [TCM Guide]"
    
    return en_title

def optimize_description(title, content, path_str):
    """Generate a CTR-boosting meta description (150-160 chars)."""
    # Get first meaningful sentence
    body = re.sub(r'<[^>]+>', '', content)
    first_para = body.split('\n')[0].strip() if body else ''
    
    # Patterns by topic
    topic = path_str.split('/')[1] if '/' in path_str else ''
    simple_title = title.split('—')[0].strip() if '—' in title else title

    # Generate compelling description based on topic
    if 'anxiety' in path_str:
        prompts = [
            f"Anxiety controlling your life? TCM identifies 4 root patterns — from Liver Qi stagnation to Heart-Spleen deficiency. Find your type and natural relief strategies.",
            f"Stressed, wired, can't relax? TCM sees anxiety differently — not just brain chemistry. Discover the 4 TCM patterns behind your anxiety and how to address each one.",
        ]
    elif 'back-pain' in path_str:
        prompts = [
            f"Chronic back pain not responding to treatment? TCM looks beyond structure — at Kidney vitality, Qi flow, and meridian blockages. A fresh perspective on relief.",
            f"Your back pain may not be about your spine. TCM reveals the hidden connections — Kidney Qi, cold-damp invasion, and blood stagnation. Explore a different approach.",
        ]
    elif 'insomnia' in path_str:
        prompts = [
            f"Can't sleep or wake at 3 AM? TCM identifies 4 distinct insomnia patterns — from Heart-Kidney imbalance to Liver Fire. Find your pattern and natural sleep solutions.",
            f"Sleep issues have different root causes in TCM. Are you Heart-Kidney imbalanced or Liver Fire blazing? Identify your pattern and restore restful sleep naturally.",
        ]
    elif 'digestion' in path_str:
        prompts = [
            f"Bloated, gassy, or irregular? TCM traces digestive issues to Spleen Qi, Stomach Heat, or Dampness patterns. Learn which one matches your symptoms and how to fix it.",
        ]
    elif 'fatigue' in path_str:
        prompts = [
            f"Always tired, no matter how much you sleep? TCM identifies Qi deficiency, Blood deficiency, and Dampness as root causes. Find yours and restore your energy.",
        ]
    elif 'headaches' in path_str:
        prompts = [
            f"Tension headaches or migraines? TCM pinpoints the pattern — Liver Fire rising, Qi stagnation, or Wind-Cold invasion. Identify your type and find targeted relief.",
        ]
    elif 'allergies' in path_str:
        prompts = [
            f"Seasonal allergies driving you crazy? TCM strengthens Wei Qi (immune defense) rather than just blocking symptoms. Natural approaches for lasting relief.",
        ]
    elif 'skin' in path_str:
        prompts = [
            f"Acne, eczema, or psoriasis? TCM treats skin as an internal issue — Blood Heat, Dampness, or Wind patterns. A holistic approach to clear, healthy skin.",
        ]
    elif 'womens' in path_str:
        prompts = [
            f"Hormonal imbalance, PMS, or menopause? TCM offers a complete system for women's health — from Liver Qi to Kidney Yin. Natural approaches that work with your body.",
        ]
    elif 'joint' in path_str or 'pain' in path_str:
        prompts = [
            f"Joint pain, arthritis, or stiffness? TCM calls it Bi Syndrome — Cold, Damp, or Wind invading the meridians. A different approach to pain relief and mobility.",
        ]
    elif 'stress' in path_str:
        prompts = [
            f"Overwhelmed, irritable, or burnt out? TCM traces stress to Liver Qi stagnation and Shen disturbance. Practical mind-body techniques backed by ancient wisdom.",
        ]
    elif 'respiratory' in path_str or 'lung' in path_str or 'cough' in path_str:
        prompts = [
            f"Chronic cough, asthma, or weak immunity? TCM strengthens Lung Qi and Wei Qi — your body's first line of defense. Natural respiratory support that works.",
        ]
    elif 'what-is-qi' in path_str:
        prompts = [
            f"Qi is your body's operating system. A clear, grounded explanation of what Qi really means in TCM — no mysticism, just practical wisdom you can apply today.",
        ]
    elif 'yin-yang' in path_str:
        prompts = [
            f"Yin and Yang isn't good vs evil. It's your body's thermostat — the ancient framework for understanding balance, health, and disease. Explained simply.",
        ]
    elif 'acupuncture' in path_str:
        prompts = [
            f"How does acupuncture actually work? Modern neuroscience is catching up to what TCM has known for centuries. A research-backed look at the needles.",
        ]
    elif 'five-elements' in path_str:
        prompts = [
            f"The Five Elements (Wood, Fire, Earth, Metal, Water) is TCM's map of the body's ecosystem. Understand your health through this ancient lens.",
        ]
    elif 'tcm-basics/' in path_str:
        prompts = [
            f"New to TCM? Start here. Clear, jargon-free explanations of Qi, Yin-Yang, meridians, and more — designed for Western readers who want real understanding.",
        ]
    elif 'treatments/' in path_str or 'therapy' in path_str:
        prompts = [
            f"Explore TCM treatment options — from acupuncture and herbs to cupping and moxibustion. What they treat, how they work, and what research says about effectiveness.",
        ]
    else:
        prompts = [
            f"{simple_title} — explored through the lens of Traditional Chinese Medicine. Understand your symptoms from a different perspective and discover natural approaches.",
            f"Learn how TCM views {simple_title.lower()}. A fresh perspective on a common health concern — no jargon, no miracle claims, just grounded wisdom.",
        ]
    
    import random
    desc = random.choice(prompts)
    
    # Ensure length is reasonable
    if len(desc) > 160:
        desc = desc[:157] + "..."
    if len(desc) < 100:
        desc = desc + f" Read the complete guide at SymptomCalm."
        if len(desc) > 160:
            desc = desc[:157] + "..."
    
    return desc

def main():
    count = 0
    for f in sorted(WORK.rglob('index.html')):
        rel = f.relative_to(WORK)
        rel_str = str(rel)
        
        # Skip
        if any(s in rel_str for s in SKIP_DIRS):
            continue
        # Skip ZH pages and legal pages
        if rel_str.startswith('zh/') or rel_str.startswith('about/') or rel_str.startswith('contact/'):
            continue
        
        with open(f) as fh:
            html = fh.read()
        
        # Get current title
        title_match = re.search(r'<title>(.*?)</title>', html)
        if not title_match:
            continue
        current_title = title_match.group(1)
        
        # Get current description
        desc_match = re.search(r'<meta name="description" content="([^"]*)"', html)
        current_desc = desc_match.group(1) if desc_match else ""
        
        # Optimize title
        new_title = optimize_title(current_title, f)
        
        # Get content for description generation
        body_match = re.search(r'<div class="article-body">(.*?)</div>', html, re.DOTALL)
        content = body_match.group(1) if body_match else ""
        
        # Optimize description
        new_desc = optimize_description(new_title, content, rel_str)
        
        # Apply changes
        changes = []
        
        if new_title != current_title:
            html = html.replace(f'<title>{current_title}</title>', f'<title>{new_title}</title>')
            html = html.replace(f'<meta property="og:title" content="{current_title}" />', f'<meta property="og:title" content="{new_title}" />')
            changes.append("title")
        
        if new_desc != current_desc:
            html = html.replace(f'<meta name="description" content="{current_desc}" />', f'<meta name="description" content="{new_desc}" />')
            html = html.replace(f'<meta property="og:description" content="{current_desc}" />', f'<meta property="og:description" content="{new_desc}" />')
            changes.append("desc")
        
        if changes:
            with open(f, 'w') as fh:
                fh.write(html)
            count += 1
            if count % 30 == 0:
                print(f"  {count}...")
    
    print(f"✅ Optimized {count} EN pages (titles + meta descriptions)")

if __name__ == "__main__":
    main()
