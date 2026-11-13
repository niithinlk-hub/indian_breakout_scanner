#!/usr/bin/env python3
"""Opus v2 picks for one stored scanner day, without changing the scanner.

Usage:  python3 opus_v2_check.py day.json [more.json ...]

day.json is a day as the scanner stores it: a replay result, or the JSON behind the Scanner backtest page
(/api/equity/backtest/<day>). Every signal in it already carries its opus and fable_op scores.

Opus v2 = side split: a long needs fable_op >= 75, a short needs opus >= 75; otherwise the live rule is
unchanged (setups A and B, signals in time order, at most 6 a day). Prints Opus's and Opus v2's picks with the
stored same-day exit-at-T1 result of each.
"""
import json
import sys

CUT, CAP, SETUPS = 75.0, 6, ("A", "B")


def v2_score(s):
    return s["scores"]["fable_op"] if s["side"] == "LONG" else s["scores"]["opus"]


def live(day, score):
    pool = [s for s in day["signals"] if s["setup"] in SETUPS and s["fut"]["T1"]["status"] != "no_data"]
    out = []
    for s in sorted(pool, key=lambda s: (s["time"], -score(s), s["symbol"])):
        if score(s) >= CUT and len(out) < CAP:
            out.append(s)
    return out


def main(paths):
    tot = {"Opus": [0, 0, 0.0], "Opus v2": [0, 0, 0.0]}
    for p in paths:
        day = json.load(open(p))
        print(day["day"])
        for name, score in (("Opus", lambda s: s["scores"]["opus"]), ("Opus v2", v2_score)):
            sel = live(day, score)
            net = sum(s["fut"]["T1"]["net_rs"] for s in sel)
            hit = sum(s["fut"]["T1"]["status"] == "target" for s in sel)
            tot[name][0] += len(sel); tot[name][1] += hit; tot[name][2] += net
            print("  %-8s %d trades, %d reached T1, exit-at-T1 net Rs %+.0f" % (name, len(sel), hit, net))
            for s in sel:
                print("      %s %-11s %-5s score %5.1f  %-8s Rs %+.0f" % (s["time"], s["symbol"], s["side"], score(s), s["fut"]["T1"]["status"], s["fut"]["T1"]["net_rs"]))
    if len(paths) > 1:
        for name, (n, hit, net) in tot.items():
            print("TOTAL %-8s %d trades, %d reached T1 (%.0f%%), net Rs %+.0f" % (name, n, hit, 100 * hit / n if n else 0, net))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
