"""Tiny dependency-free SVG chart helpers for the HTML report (theme tokens via CSS vars)."""
from __future__ import annotations

import html
import math

import numpy as np


def esc(x) -> str:
    return html.escape(str(x))


def _nice_ticks(lo: float, hi: float, n: int = 5) -> list[float]:
    if hi <= lo:
        hi = lo + 1
    span = hi - lo
    raw = span / n
    mag = 10 ** math.floor(math.log10(raw))
    step = min((s * mag for s in (1, 2, 2.5, 5, 10) if s * mag >= raw), default=raw)
    start = math.floor(lo / step) * step
    ticks = []
    v = start
    while v <= hi + 1e-9:
        if v >= lo - 1e-9:
            ticks.append(round(v, 10))
        v += step
    return ticks


def fmt_inr(v: float) -> str:
    a = abs(v)
    s = "-" if v < 0 else ""
    if a >= 1e7:
        return f"{s}₹{a / 1e7:.2f} Cr"
    if a >= 1e5:
        return f"{s}₹{a / 1e5:.2f} L"
    if a >= 1e3:
        return f"{s}₹{a / 1e3:.1f}k"
    return f"{s}₹{a:.0f}"


def line_chart(series: list[dict], width=760, height=280, y_fmt=fmt_inr, x_labels=None, zero_line=True,
               title="", marker_index=None, marker_label="") -> str:
    """series: [{name, x (list of str dates), y (list of float), cls}] — shared x positions by index."""
    pad_l, pad_r, pad_t, pad_b = 64, 16, 14, 30
    allv = [v for s in series for v in s["y"] if v is not None and np.isfinite(v)]
    if not allv:
        return ""
    lo, hi = min(allv), max(allv)
    if zero_line:
        lo, hi = min(lo, 0), max(hi, 0)
    ticks = _nice_ticks(lo, hi)
    lo, hi = min(lo, ticks[0]), max(hi, ticks[-1])
    n = max(len(s["y"]) for s in series)
    w = width - pad_l - pad_r
    h = height - pad_t - pad_b

    def X(i):
        return pad_l + (w * i / max(n - 1, 1))

    def Y(v):
        return pad_t + h - (v - lo) / (hi - lo) * h

    out = [f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}">']
    for t in ticks:
        out.append(f'<line class="grid" x1="{pad_l}" x2="{width - pad_r}" y1="{Y(t):.1f}" y2="{Y(t):.1f}"/>')
        out.append(f'<text class="tick" x="{pad_l - 6}" y="{Y(t) + 4:.1f}" text-anchor="end">{esc(y_fmt(t))}</text>')
    if zero_line and lo < 0 < hi:
        out.append(f'<line class="zero" x1="{pad_l}" x2="{width - pad_r}" y1="{Y(0):.1f}" y2="{Y(0):.1f}"/>')
    if x_labels:
        idxs = sorted(set([0, n - 1] + [int(round(k * (n - 1) / 5)) for k in range(1, 5)]))
        for i in idxs:
            if i < len(x_labels):
                anchor = "start" if i == 0 else ("end" if i == n - 1 else "middle")
                out.append(f'<text class="tick" x="{X(i):.1f}" y="{height - 8}" text-anchor="{anchor}">{esc(x_labels[i])}</text>')
    if marker_index is not None:
        mx = X(marker_index)
        out.append(f'<rect class="band" x="{mx:.1f}" y="{pad_t}" width="{width - pad_r - mx:.1f}" height="{h}"/>')
        out.append(f'<line class="marker" x1="{mx:.1f}" x2="{mx:.1f}" y1="{pad_t}" y2="{pad_t + h}"/>')
        out.append(f'<text class="tick mk" x="{mx + 6:.1f}" y="{pad_t + 14}">{esc(marker_label)}</text>')
    for s in series:
        pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(s["y"]) if v is not None and np.isfinite(v))
        out.append(f'<polyline class="line {s.get("cls", "s1")}" points="{pts}"/>')
        if s["y"]:
            i = len(s["y"]) - 1
            out.append(f'<circle class="dot {s.get("cls", "s1")}" cx="{X(i):.1f}" cy="{Y(s["y"][-1]):.1f}" r="3.5"/>')
    out.append("</svg>")
    return "".join(out)


def bar_chart(labels: list[str], values: list[float], width=760, height=240, y_fmt=fmt_inr, title="",
              highlight=None) -> str:
    pad_l, pad_r, pad_t, pad_b = 64, 10, 14, 44
    vals = [0 if (v is None or not np.isfinite(v)) else v for v in values]
    lo, hi = min(min(vals), 0), max(max(vals), 0)
    ticks = _nice_ticks(lo, hi)
    lo, hi = min(lo, ticks[0]), max(hi, ticks[-1])
    n = len(vals)
    w = width - pad_l - pad_r
    h = height - pad_t - pad_b
    bw = w / max(n, 1)

    def Y(v):
        return pad_t + h - (v - lo) / (hi - lo) * h

    out = [f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}">']
    for t in ticks:
        out.append(f'<line class="grid" x1="{pad_l}" x2="{width - pad_r}" y1="{Y(t):.1f}" y2="{Y(t):.1f}"/>')
        out.append(f'<text class="tick" x="{pad_l - 6}" y="{Y(t) + 4:.1f}" text-anchor="end">{esc(y_fmt(t))}</text>')
    for i, (lab, v) in enumerate(zip(labels, vals)):
        x = pad_l + i * bw + bw * 0.15
        y0, y1 = Y(max(v, 0)), Y(min(v, 0))
        cls = "pos" if v >= 0 else "neg"
        if highlight and lab in highlight:
            cls += " hl"
        out.append(f'<rect class="bar {cls}" x="{x:.1f}" y="{y0:.1f}" width="{bw * 0.7:.1f}" height="{max(y1 - y0, 0.5):.1f}"><title>{esc(lab)}: {esc(y_fmt(v))}</title></rect>')
        if i % max(1, math.ceil(n / 9)) == 0:
            out.append(f'<text class="tick" x="{x + bw * 0.35:.1f}" y="{height - pad_b + 14}" text-anchor="middle">{esc(lab)}</text>')
    out.append(f'<line class="zero" x1="{pad_l}" x2="{width - pad_r}" y1="{Y(0):.1f}" y2="{Y(0):.1f}"/>')
    out.append("</svg>")
    return "".join(out)
