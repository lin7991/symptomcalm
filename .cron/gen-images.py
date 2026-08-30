#!/usr/bin/env python3
"""Generate SVG hero images for all symptom categories + og:image support."""
import os
from pathlib import Path

WORK = Path(os.path.expanduser("~/symptomcalm"))
IMG_DIR = WORK / "images"
IMG_DIR.mkdir(exist_ok=True)

# SVG template with gradient + emoji icon + title
SVG_TEMPLATE = '''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#1A535C"/>
      <stop offset="100%" style="stop-color:#2C7A7B"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="630" fill="url(#bg)"/>
  <circle cx="1000" cy="100" r="200" fill="rgba(255,255,255,0.05)"/>
  <circle cx="150" cy="550" r="250" fill="rgba(255,255,255,0.04)"/>
  <text x="600" y="280" font-family="Apple Color Emoji, Segoe UI Emoji, Noto Color Emoji" font-size="160" text-anchor="middle">{{ICON}}</text>
  <text x="600" y="430" font-family="Inter, Arial, sans-serif" font-size="52" font-weight="700" fill="#FFFFFF" text-anchor="middle">{{TITLE}}</text>
  <text x="600" y="490" font-family="Inter, Arial, sans-serif" font-size="28" fill="rgba(255,255,255,0.8)" text-anchor="middle">SymptomCalm — Ancient Wisdom. Modern Clarity.</text>
  <rect x="500" y="520" width="200" height="4" rx="2" fill="#D69E2E"/>
</svg>
'''

# Category → (icon, title)
CATEGORIES = {
    "anxiety": ("🧠", "Anxiety & Stress"),
    "back-pain": ("🦴", "Chronic Back Pain"),
    "insomnia": ("🌙", "Insomnia & Sleep"),
    "digestion": ("🍚", "Digestive Health"),
    "headaches": ("🤕", "Headaches"),
    "fatigue": ("⚡", "Chronic Fatigue"),
    "allergies": ("🤧", "Allergies"),
    "skin-conditions": ("🧴", "Skin Health"),
    "womens-health": ("🌸", "Women's Health"),
    "joint-pain": ("🦵", "Joint Pain"),
    "stress": ("🌿", "Stress & Burnout"),
    "respiratory-health": ("🫁", "Respiratory Health"),
    "mental-emotional-health": ("💭", "Mental & Emotional Health"),
    "tcm-basics": ("☯️", "TCM Basics"),
    "treatments": ("📿", "TCM Treatments"),
    "eye-health": ("👁️", "Eye Health"),
    "ear-health-tinnitus": ("👂", "Ear Health & Tinnitus"),
}

created = 0
for cat, (icon, title) in CATEGORIES.items():
    svg = SVG_TEMPLATE.replace("{{ICON}}", icon).replace("{{TITLE}}", title)
    path = IMG_DIR / f"{cat}.svg"
    with open(path, "w") as f:
        f.write(svg)
    created += 1

# Default/fallback image
with open(IMG_DIR / "default.svg", "w") as f:
    f.write(SVG_TEMPLATE.replace("{{ICON}}", "☯️").replace("{{TITLE}}", "Traditional Chinese Medicine"))

print(f"✅ Created {created + 1} SVG images in /images/")
for p in sorted(IMG_DIR.glob("*.svg")):
    print(f"  {p.name} ({p.stat().st_size}B)")
