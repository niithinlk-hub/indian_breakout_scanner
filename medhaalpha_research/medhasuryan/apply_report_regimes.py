"""Adds each stored day's Nifty trend ("nifty_regime") to the scanner's two stored backtest reports, so the app's
stored backtest pages can show MedhaSuryan's real picks. Run once after applying medhasuryan_integration.patch:

    python apply_report_regimes.py <app folder that holds engine/ and scanner/>

It changes a report only if it is the version the patch was built on (14 Nov 2026) and checks the result by its
SHA-256; a report already updated is left alone. Uses the labels in report_regimes.json (next to this file)."""
import hashlib, json, os, sys

app = sys.argv[1] if len(sys.argv) > 1 else "."
spec = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "report_regimes.json"), encoding="utf-8"))
ok = True
for rel, s in spec["files"].items():
    path = os.path.join(app, *rel.split("/"))
    raw = open(path, "rb").read()
    sha = hashlib.sha256(raw).hexdigest()
    if sha == s["after_sha256"]:
        print("already updated:", rel)
        continue
    if sha != s["before_sha256"]:
        print("NOT CHANGED, not the 14 Nov 2026 version this was built on:", rel)
        ok = False
        continue
    doc = json.loads(raw.decode("utf-8"))
    for d in doc["days"]:
        d["nifty_regime"] = s["nifty_regime"][d["day"]]
    out = json.dumps(doc, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if hashlib.sha256(out).hexdigest() != s["after_sha256"]:
        print("NOT CHANGED, result differs from the tested file:", rel)
        ok = False
        continue
    tmp = path + ".tmp"
    open(tmp, "wb").write(out)
    os.replace(tmp, path)
    print("updated:", rel)
sys.exit(0 if ok else 1)
