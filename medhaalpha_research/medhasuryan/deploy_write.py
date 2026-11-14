import base64, hashlib, io, json, lzma, os, shutil, sys, tarfile
ROOT = '/opt/vitezza'
BK = ROOT + '/backups/medhasuryan-2026-11-14'
P = json.loads(PAYLOAD)
MODE = os.environ.get('MODE', 'check')          # check | write | rollback


def h(p):
    with open(p, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def put(path, data, like):
    st = os.stat(like)
    tmp = path + '.medhasuryan-tmp'
    with open(tmp, 'wb') as fh:
        fh.write(data)
    os.chmod(tmp, st.st_mode & 0o7777)
    os.chown(tmp, st.st_uid, st.st_gid)
    os.replace(tmp, path)


raw = base64.b64decode(P['code_b64'])
assert hashlib.sha256(raw).hexdigest() == P['code_sha'], 'payload damaged'
man = P['manifest']
state = {}
for f, m in man.items():
    cur = h(ROOT + '/' + f)
    state[f] = 'base' if cur == m['base'] else 'new' if cur == m['new'] else 'OTHER'
    print('STATE', state[f], f, flush=True)
if MODE == 'rollback':
    for f in man:
        b = BK + '/' + f
        if state[f] == 'new' and os.path.exists(b) and h(b) == man[f]['base']:
            with open(b, 'rb') as fh:
                put(ROOT + '/' + f, fh.read(), ROOT + '/' + f)
            print('RESTORED', f, flush=True)
    print('ROLLBACK DONE', flush=True)
    sys.exit(0)
if any(v == 'OTHER' for v in state.values()):
    print('ABORT: a file on the server is not the version this change was built and tested on; nothing written', flush=True)
    sys.exit(1)
if MODE != 'write':
    print('CHECK OK: every file is the tested version or already updated', flush=True)
    sys.exit(0)
for f in man:                                    # back up the files about to change (never overwrite a backup)
    if state[f] == 'base':
        b = BK + '/' + f
        os.makedirs(os.path.dirname(b), exist_ok=True)
        if not os.path.exists(b):
            shutil.copy2(ROOT + '/' + f, b)
        assert h(b) == man[f]['base'], 'backup check failed: ' + f
print('BACKUP', BK, flush=True)
with tarfile.open(fileobj=io.BytesIO(lzma.decompress(raw)), mode='r:') as tf:
    for ti in tf.getmembers():
        data = tf.extractfile(ti).read()
        assert hashlib.sha256(data).hexdigest() == man[ti.name]['new'], 'new file hash ' + ti.name
        if state[ti.name] == 'base':
            put(ROOT + '/' + ti.name, data, ROOT + '/' + ti.name)
            print('WROTE', ti.name, flush=True)
for f, days in P['regimes'].items():
    if state[f] != 'base':
        continue
    with open(ROOT + '/' + f, encoding='utf-8') as fh:
        doc = json.load(fh)
    for d in doc['days']:
        d['nifty_regime'] = days[d['day']]
    out = json.dumps(doc, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    assert hashlib.sha256(out).hexdigest() == man[f]['new'], 'report rewrite hash ' + f
    put(ROOT + '/' + f, out, ROOT + '/' + f)
    print('WROTE', f, flush=True)
bad = [f for f in man if h(ROOT + '/' + f) != man[f]['new']]
print('VERIFY', 'all files are the new version' if not bad else 'MISMATCH ' + ' '.join(bad), flush=True)
