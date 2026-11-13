import base64, hashlib, json, os, zlib
import scanner.equity.validation as v
R = v.REPORT_FILE.parent
print("===DIR", json.dumps(sorted([f, os.path.getsize(R / f)] for f in os.listdir(R))), "| cwd", os.getcwd(), json.dumps(sorted(os.listdir("."))[:40]), flush=True)
scripts = {}
for d in ("scripts", "../scripts", "/app/scripts"):
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if f.startswith("eq_backtest") and f.endswith(".py"):
                scripts[f] = open(os.path.join(d, f), encoding="utf-8").read()
        break
print("===SCRIPTS", json.dumps({k: len(x) for k, x in scripts.items()}), flush=True)
six = json.load(open(R / "backtest6m.json", encoding="utf-8"))
sig = json.load(open(R / "backtest6m_signals.json", encoding="utf-8"))


def brief(x):
    s = json.dumps(x)
    if len(s) < 1200:
        return x
    return "<%d chars %s %s>" % (len(s), type(x).__name__, ",".join(str(k) for k in list(x)[:25]) if isinstance(x, dict) else len(x))


print("===META6", json.dumps({k: brief(x) for k, x in six.items()}), flush=True)
print("===METAS", json.dumps({k: brief(x) for k, x in sig.items()}), flush=True)
print("===DAY0", json.dumps(sig["days"][0])[:1500], flush=True)
BUDGET = 1000000


def pack(lo, hi, full):
    doc = {"scripts": scripts,
           "six": {k: x for k, x in six.items() if full or k not in ("by_setups",)},
           "sig": {**{k: x for k, x in sig.items() if k != "days"}, "days": [d for d in sig["days"] if lo <= d["day"] <= hi]}}
    raw = json.dumps(doc, separators=(",", ":")).encode()
    return raw, base64.b64encode(zlib.compress(raw, 9)).decode()


for lo, hi, full in (("2026-01-01", "2026-12-31", True), ("2026-01-01", "2026-12-31", False), ("2026-08-01", "2026-12-31", False),
                     ("2026-09-01", "2026-10-20", False), ("2026-09-01", "2026-09-30", False)):
    raw, b64 = pack(lo, hi, full)
    print("===TRY", lo, hi, full, len(raw), len(b64), flush=True)
    if len(b64) <= BUDGET:
        break
print("===SHA", hashlib.sha256(raw).hexdigest(), len(raw), flush=True)
print("===B64", flush=True)
W = 4000
for i in range(0, len(b64), W):
    print(b64[i:i + W], flush=True)
print("===END", flush=True)
