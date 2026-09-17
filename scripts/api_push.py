#!/usr/bin/env python3
"""Push local HEAD -> GitHub via Git Data API, with per-request payload files and
hash verification of every uploaded blob.

Usage: python3 api_push4.py [--apply] [--msg "..."]
"""
import json, base64, subprocess, os, re, sys, hashlib, uuid
from concurrent.futures import ThreadPoolExecutor

TOKEN = open('/tmp/gh_token.txt').read().strip()
API = "https://api.github.com/repos/lin7991/symptomcalm"
ROOT = "/Users/xj/symptomcalm"

apply = '--apply' in sys.argv
msg = "sync"
if '--msg' in sys.argv:
    msg = sys.argv[sys.argv.index('--msg') + 1]


def api(method, path, payload=None):
    cmd = ['curl', '-s', '--max-time', '60', '-X', method,
           '-H', 'Authorization: Bearer ' + TOKEN,
           '-H', 'Accept: application/vnd.github+json']
    tmp = None
    if payload is not None:
        tmp = f'/tmp/ghpayload-{uuid.uuid4().hex}.json'
        with open(tmp, 'w') as f:
            json.dump(payload, f)
        cmd += ['-H', 'Content-Type: application/json', '-d', '@' + tmp]
    cmd.append(API + path)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        try:
            return json.loads(r.stdout)
        except Exception:
            return {'_raw': r.stdout[:300], '_err': r.stderr[:200]}
    finally:
        if tmp and os.path.exists(tmp):
            os.remove(tmp)


def git_blob_sha(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def norm(data):
    return b''.join(l for l in data.splitlines(keepends=True) if l.strip() != b'')


os.chdir(ROOT)

ref = api('GET', '/git/ref/heads/main')
remote_head = ref['object']['sha']
commit = api('GET', '/git/commits/' + remote_head)
remote_tree_sha = commit['tree']['sha']
tree = api('GET', f'/git/trees/{remote_tree_sha}?recursive=1')
if 'tree' not in tree:
    print('TREE FETCH FAIL', tree); sys.exit(1)
remote = {i['path']: i['sha'] for i in tree['tree'] if i['type'] == 'blob'}
print('remote head:', remote_head, '| blobs:', len(remote))

out = subprocess.run(['git', 'ls-tree', '-r', 'HEAD'], capture_output=True, text=True).stdout
local = {}
for line in out.strip().split('\n'):
    if not line:
        continue
    meta, path = line.split('\t', 1)
    local[path] = meta.split()[2]

cands = sorted(p for p, s in local.items() if remote.get(p) != s)
print('candidates:', len(cands))


def classify(p):
    rsha = remote.get(p)
    if rsha is None:
        return p, 'real'
    b = api('GET', '/git/blobs/' + rsha)
    if 'content' not in b:
        return p, 'real'
    if norm(base64.b64decode(b['content'])) == norm(open(os.path.join(ROOT, p), 'rb').read()):
        return p, 'noise'
    return p, 'real'


results = {}
with ThreadPoolExecutor(max_workers=6) as ex:
    for i, (p, k) in enumerate(ex.map(classify, cands), 1):
        results[p] = k
        if i % 200 == 0:
            print(f'  classified {i}/{len(cands)}', flush=True)

real = sorted(p for p, k in results.items() if k == 'real')
print(f'real: {len(real)} | whitespace-only: {len(results) - len(real)}')
for p in real[:40]:
    print('   REAL', p)

if not apply:
    print('DRY-RUN')
    sys.exit(0)
if not real:
    print('nothing to push')
    sys.exit(0)

print('uploading', len(real), 'blobs (serialized, hash-verified)...')
items = []
for i, p in enumerate(real, 1):
    raw = open(os.path.join(ROOT, p), 'rb').read()
    expect = git_blob_sha(raw)
    b = api('POST', '/git/blobs', {'content': base64.b64encode(raw).decode(),
                                   'encoding': 'base64'})
    if 'sha' not in b:
        print('BLOB FAIL', p, b); sys.exit(1)
    if b['sha'] != expect:
        print('HASH MISMATCH for', p, b['sha'], '!=', expect); sys.exit(1)
    items.append({'path': p, 'mode': '100644', 'type': 'blob', 'sha': b['sha']})
    print(f'  [{i}/{len(real)}] {p} -> {b["sha"][:10]} (verified)')
print('all', len(items), 'blobs verified')

t = api('POST', '/git/trees', {'base_tree': remote_tree_sha, 'tree': items})
if 'sha' not in t:
    print('TREE FAIL', t); sys.exit(1)
c = api('POST', '/git/commits', {'message': msg, 'tree': t['sha'], 'parents': [remote_head]})
if 'sha' not in c:
    print('COMMIT FAIL', c); sys.exit(1)
print('new commit:', c['sha'])
res = api('PATCH', '/git/refs/heads/main', {'sha': c['sha'], 'force': False})
if res.get('ref'):
    print('PUSH SUCCESS ->', res['object']['sha'])
else:
    print('PUSH FAIL:', res)
    sys.exit(1)

# post-push read-back verification
print('\n--- READ-BACK VERIFICATION ---')
ref2 = api('GET', '/git/ref/heads/main')
commit2 = api('GET', '/git/commits/' + ref2['object']['sha'])
tree2 = api('GET', f"/git/trees/{commit2['tree']['sha']}?recursive=1")
remote2 = {i['path']: i['sha'] for i in tree2['tree'] if i['type'] == 'blob'}
ok = True
for p in real:
    got = remote2.get(p)
    want = local[p]
    match = got == want
    ok = ok and match
    print(f'  {"OK  " if match else "FAIL"} {p} remote={str(got)[:10]} local={want[:10]}')
print('ALL MATCH:', ok)
sys.exit(0 if ok else 1)
