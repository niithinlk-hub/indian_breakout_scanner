#!/usr/bin/env python3
"""Opus, Opus v2 and Opus v3 picks for stored scanner days, without changing the scanner.

Usage:  python3 opus_v3_check.py day.json [more.json ...]

day.json is a day as the scanner stores it: a replay result, or the JSON behind the Scanner backtest page
(/api/equity/backtest/<day>). Every signal in it already carries its opus and fable_op scores and its rel_vol.

  Opus v2  a long needs fable_op >= 75, a short needs opus >= 75.
  Opus v3  Opus v2, and a long also needs rel_vol >= 1 (a missing rel_vol passes).
Otherwise the live rule is unchanged: setups A and B, signals in time order, at most 6 a day.
Prints each model's picks with the stored same-day exit-at-T1 result.
"""
import json
import sys

CUT, CAP, SETUPS, MIN_REL_VOL = 75.0, 6, ("A", "B"), 1.0


def v2_score(s):
    return s["scores"]["fable_op"] if s["side"] == "LONG" else s["scores"]["opus"]


def v3_score(s):
    rv = (s.get("snapshot") or {}).get("rel_vol", s.get("rel_vol"))
    if s["side"] == "LONG" and rv is not None and rv < MIN_REL_VOL:
        return 0.0
    return v2_score(s)


def live(day, score):
    pool = [s for s in day["signals"] if s["setup"] in SETUPS and s["fut"]["T1"]["status"] != "no_data"]
    out = []
    for s in sorted(pool, key=lambda s: (s["time"], -score(s), s["symbol"])):
        if score(s) >= CUT and len(out) < CAP:
            out.append(s)
    return out


def main(paths):
    models = (("Opus", lambda s: s["scores"]["opus"]), ("Opus v2", v2_score), ("Opus v3", v3_score))
    tot = {name: [0, 0, 0, 0.0] for name, _ in models}
    for p in paths:
        day = json.load(open(p))
        print(day["day"])
        for name, score in models:
            sel = live(day, score)
            net = sum(s["fut"]["T1"]["net_rs"] for s in sel)
            hit = sum(s["fut"]["T1"]["status"] == "target" for s in sel)
            stop = sum(s["fut"]["T1"]["status"] == "stopped" for s in sel)
            t = tot[name]
            t[0] += len(sel); t[1] += hit; t[2] += stop; t[3] += net
            print("  %-8s %d trades, %d reached T1, %d stopped, exit-at-T1 net Rs %+.0f" % (name, len(sel), hit, stop, net))
            for s in sel:
                print("      %s %-11s %-5s score %5.1f  %-8s Rs %+.0f" % (s["time"], s["symbol"], s["side"], score(s), s["fut"]["T1"]["status"], s["fut"]["T1"]["net_rs"]))
    if len(paths) > 1:
        for name, (n, hit, stop, net) in tot.items():
            print("TOTAL %-8s %d trades, %d reached T1 (%.0f%%), %d stopped (%.0f%%), net Rs %+.0f" % (name, n, hit, 100 * hit / n if n else 0, stop, 100 * stop / n if n else 0, net))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
