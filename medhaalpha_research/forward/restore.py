#!/usr/bin/env python3
"""Rebuild the forward test folder from the two published files.
usage: restore.py <bundle.json> <state.json> <base_dir>
Run it with -I, from a directory other than the one holding the downloads. Line endings are kept as stored."""
import json, os, sys
bundle, state, base = sys.argv[1], sys.argv[2], os.path.abspath(sys.argv[3])
n = 0
for rel, text in json.load(open(bundle, encoding="utf-8"))["files"].items():
    assert not os.path.isabs(rel) and ".." not in rel.split("/"), rel
    p = os.path.join(base, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "wb").write(text.encode("utf-8"))
    n += 1
st = json.load(open(state, encoding="utf-8"))
S = os.path.join(base, "state")
os.makedirs(os.path.join(S, "days"), exist_ok=True)
for day, doc in (st.get("days") or {}).items():
    assert len(day) == 10 and day[4] == "-" and day[7] == "-" and day.replace("-", "").isdigit(), day
    json.dump(doc, open(os.path.join(S, "days", day + ".json"), "w"))
if st.get("no_session"):
    json.dump(st["no_session"], open(os.path.join(S, "no_session.json"), "w"))
print("restored %d code files and %d stored days into %s" % (n, len(st.get("days") or {}), base))
