#!/usr/bin/env python3
"""Apply the publisher's deterministic release metadata to one generated page."""
import importlib.util
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = root / '.cron' / 'publish-article.py'
spec = importlib.util.spec_from_file_location('publish_article', source)
if spec is None or spec.loader is None:
    raise SystemExit('cannot load publish-article.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

if len(sys.argv) != 2:
    raise SystemExit('usage: ensure-release-metadata.py RELATIVE_HTML_PATH')
rel = sys.argv[1].strip('/')
path = root / rel
if not path.is_file():
    raise SystemExit(f'missing page: {rel}')
old = path.read_text(encoding='utf-8')
new = module.ensure_release_metadata(old, rel)
path.write_text(new, encoding='utf-8')
print(f'METADATA_OK {rel}')
