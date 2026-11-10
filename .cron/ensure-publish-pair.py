#!/usr/bin/env python3
"""Require and wire the EN/ZH pair for one published article."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://symptomcalm.com"


def add_link(path: Path, hreflang: str, href: str) -> None:
    text = path.read_text(encoding="utf-8")
    if f'hreflang="{hreflang}"' in text:
        return
    tag = f'  <link rel="alternate" hreflang="{hreflang}" href="{href}" />\n'
    if "</head>" not in text:
        raise RuntimeError(f"missing </head>: {path}")
    path.write_text(text.replace("</head>", tag + "</head>", 1), encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: ensure-publish-pair.py /path/to/article/", file=sys.stderr)
        return 2
    article = sys.argv[1].strip("/")
    en = ROOT / article / "index.html"
    zh = ROOT / "zh" / article / "index.html"
    if not en.exists() or not zh.exists():
        print(f"PAIR_MISSING en={en.exists()} zh={zh.exists()} article=/{article}/", file=sys.stderr)
        return 1
    en_url = f"{BASE}/{article}/"
    zh_url = f"{BASE}/zh/{article}/"
    add_link(en, "zh", zh_url)
    add_link(zh, "en", en_url)
    add_link(en, "x-default", en_url)
    add_link(zh, "x-default", en_url)
    print(f"PAIR_OK /{article}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
