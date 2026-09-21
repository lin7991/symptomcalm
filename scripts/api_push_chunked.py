#!/usr/bin/env python3
"""Chunked API push: builds the tree in batches so the /git/trees payload never
gets large enough for GitHub to time out (422).

Usage: python3 api_push_chunked.py [--apply] [--batch 100] [--msg "..."]
Phase C references existing blob SHAs (content-addressed, already uploaded by
earlier runs); if the tree call complains, the batch's blobs are uploaded then retried.
"""
import json, base64, subprocess, os, sys, uuid, hashlib

TOKEN = open('/tmp/gh_token.txt').read().strip()
API = "https://api.github.com/repos/lin7991/symptomcalm"
ROOT = "/Users/xj/symptomcalm"

apply = '--apply' in sys.argv
batch_size = 100
if '--batch' in sys.argv:
    batch_size = int(sys.argv[sys.argv.index('--batch') + 1])
msg = "sync"
if '--msg' in sys.argv:
    msg = sys.argv[sys.argv.index('--msg') + 1]


def api(method, path, payload=None):
    cmd = ['curl', '-s', '--max-time', '120', '-X', method,
           '-H', 'Authorization: token ' + TOKEN,
           '-H', 'Accept: application/vnd.github+json']
    tmp = None
    if payload is not None:
        tmp = f'/tmp/ghpayload-{uuid.uuid4().hex}.json'
        with open(tmp, 'w') as f:
            json.dump(payload, f)
        cmd += ['-H', 'Content-Type: application/json', '-d', '@' + tmp]
    cmd.append(API + path)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        try:
            return json.loads(r.stdout)
        except Exception:
            return {'_raw': r.stdout[:400], '_err': r.stderr[:300]}
    finally:
        if tmp and os.path.exists(tmp):
            os.remove(tmp)


def git_blob_sha(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


os.chdir(ROOT)

ref = api('GET', '/git/ref/heads/main')
remote_head = ref['object']['sha']
commit = api('GET', '/git/commits/' + remote_head)
cur_tree = commit['tree']['sha']
tree = api('GET', f'/git/trees/{cur_tree}?recursive=1')
if 'tree' not in tree:
    print('TREE FETCH FAIL', tree)
    sys.exit(1)
remote = {i['path']: i['sha'] for i in tree['tree'] if i['type'] == 'blob'}
print('remote head:', remote_head, '| blobs:', len(remote), '| truncated:', tree.get('truncated'))

out = subprocess.run(['git', 'ls-tree', '-r', 'HEAD'], capture_output=True, text=True).stdout
local = {}
for line in out.strip().split('\n'):
    if not line:
        continue
    meta, path = line.split('\t', 1)
    local[path] = meta.split()[2]

cands = sorted(p for p, s in local.items() if remote.get(p) != s)
print('candidates (sha differs):', len(cands))
if not cands:
    print('nothing to push')
    sys.exit(0)
if not apply:
    print('DRY-RUN')
    sys.exit(0)

pushed_items = []
for i in range(0, len(cands), batch_size):
    chunk = cands[i:i + batch_size]
    items = [{'path': p, 'mode': '100644', 'type': 'blob', 'sha': local[p]} for p in chunk]
    t = api('POST', '/git/trees', {'base_tree': cur_tree, 'tree': items})
    if 'sha' not in t:
        # blobs may be missing on the server -> upload, verify, retry
        print(f'  batch {i//batch_size+1}: tree rejected, uploading blobs...')
        for p in chunk:
            raw = open(os.path.join(ROOT, p), 'rb').read()
            expect = git_blob_sha(raw)
            b = api('POST', '/git/blobs', {'content': base64.b64encode(raw).decode(), 'encoding': 'base64'})
            if 'sha' not in b or b['sha'] != expect:
                print('BLOB FAIL', p, b)
                sys.exit(1)
        t = api('POST', '/git/trees', {'base_tree': cur_tree, 'tree': items})
        if 'sha' not in t:
            print('TREE FAIL', t)
            sys.exit(1)
    cur_tree = t['sha']
    c = api('POST', '/git/commits', {'message': f'{msg} [{i//batch_size+1}]', 'tree': cur_tree, 'parents': [remote_head]})
    if 'sha' not in c:
        print('COMMIT FAIL', c)
        sys.exit(1)
    remote_head = c['sha']
    pushed_items.extend(chunk)
    print(f'  batch {i//batch_size+1}/{(len(cands)+batch_size-1)//batch_size}: {len(chunk)} files -> commit {c["sha"][:10]}', flush=True)
    r = api('PATCH', '/git/refs/heads/main', {'sha': remote_head, 'force': False})
    if not r.get('ref'):
        print('REF UPDATE FAIL', r)
        sys.exit(1)

print(f'\npushed {len(pushed_items)} files in {len(range(0, len(cands), batch_size))} commits')

print('\n--- READ-BACK VERIFICATION ---')
ref2 = api('GET', '/git/ref/heads/main')
commit2 = api('GET', '/git/commits/' + ref2['object']['sha'])
tree2 = api('GET', f"/git/trees/{commit2['tree']['sha']}?recursive=1")
remote2 = {i['path']: i['sha'] for i in tree2['tree'] if i['type'] == 'blob'}
bad = [p for p in pushed_items if remote2.get(p) != local[p]]
for p in bad[:20]:
    print('  FAIL', p, 'remote=', str(remote2.get(p))[:10], 'local=', local[p][:10])
print('PUSHED ITEMS MATCH:', not bad, f'({len(pushed_items) - len(bad)}/{len(pushed_items)})')

# Full-tree safety check (see symptomcalm-infrastructure references/api-push-safety.md):
# a partial remote tree can drop CNAME/.nojekyll/index.html -> whole-site 404.
missing = [p for p in local if p not in remote2]
mismatch = [p for p in local if remote2.get(p) != local[p]]
print('local blobs:', len(local), '| remote blobs:', len(remote2))
print('MISSING on remote:', len(missing), missing[:10])
print('STILL MISMATCHED:', len(mismatch))
ROOT_FILES = ['CNAME', '.nojekyll', 'index.html', 'styles/style.css', 'js/site.js', 'sitemap.xml']
ok_root = all(p in remote2 for p in ROOT_FILES)
print('ROOT FILES PRESENT:', ok_root, [p for p in ROOT_FILES if p not in remote2])
sys.exit(0 if (not bad and not missing and ok_root) else 1)

