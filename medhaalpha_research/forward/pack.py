#!/usr/bin/env python3
"""Pack the forward test for publishing.  usage: pack.py <base_dir> <out_dir> [--code]
Writes <out_dir>/state.json (everything under state/: totals, every stored day, the summary text) and, with
--code, <out_dir>/bundle.json (the frozen scanner copy, the job scripts, the runbook and the rules)."""
import json, os, sys
base, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
os.makedirs(out, exist_ok=True)
S = os.path.join(base, "state")
rd = lambda p: open(p, encoding="utf-8").read()
state = {"log": json.load(open(os.path.join(S, "log.json"))) if os.path.exists(os.path.join(S, "log.json")) else None,
         "summary_md": rd(os.path.join(S, "summary.md")) if os.path.exists(os.path.join(S, "summary.md")) else "",
         "no_session": json.load(open(os.path.join(S, "no_session.json"))) if os.path.exists(os.path.join(S, "no_session.json")) else [],
         "days": {f[:-5]: json.load(open(os.path.join(S, "days", f))) for f in sorted(os.listdir(os.path.join(S, "days"))) if f.endswith(".json")},
         "protocol_md": rd(os.path.join(base, "protocol.md"))}
json.dump(state, open(os.path.join(out, "state.json"), "w"), separators=(",", ":"))
print("state.json: %d days, %d bytes" % (len(state["days"]), os.path.getsize(os.path.join(out, "state.json"))))
if "--code" in sys.argv:
    files = {}
    for root, dirs, names in os.walk(base):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", "venv", "tmp", "state", "out")]
        for n in names:
            if n.endswith((".py", ".md", ".txt", ".html")):
                p = os.path.join(root, n)
                files[os.path.relpath(p, base)] = open(p, "rb").read().decode("utf-8")
    json.dump({"files": files}, open(os.path.join(out, "bundle.json"), "w"), separators=(",", ":"))
    print("bundle.json: %d files, %d bytes" % (len(files), os.path.getsize(os.path.join(out, "bundle.json"))))
