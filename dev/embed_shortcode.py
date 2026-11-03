#!/usr/bin/env python3
"""Fit column-width [iframe] height formulas from dev/heights.json
(written from dev/measure.html) and emit dev/shortcodes.txt.

The embed sits in Mongabay's article column, COL = min(780px,
100vw - 2*clamp(20px, 1px + 5vw, 40px)), and the page is forced into its
stacked layout at every embed width (see the body.solo.fill media rule),
so each figure's height is one smooth function of COL: an upper envelope
of at most two lines. `?fill=1` turns the formula's spare pixels into
block spacing. Re-run after ANY copy or layout change (re-measure first).
"""
import json

PAD = 10     # wrap + classic-scrollbar allowance — adjust here
COL = "min(780px, 100vw - 2*clamp(20px, 1px + 5vw, 40px))"


def seg_envelope(pts):
    """One or two lines whose max covers all points."""
    lo = min(pts, key=lambda p: p[1])
    segs = [p for p in (pts[:pts.index(lo) + 1], pts[pts.index(lo):]) if len(p) > 1]
    lines = []
    for s in segs:
        (x0, y0), (x1, y1) = s[0], s[-1]
        b = (y1 - y0) / (x1 - x0) if x1 != x0 else 0.0
        a = y0 - b * x0
        a += max(y - (a + b * x) for x, y in s)       # raise to cover
        lines.append((a, b))
    if len(lines) == 1 or abs(lines[0][1] - lines[1][1]) < 1e-9:
        return lines[:1]
    return lines


def css_line(a, b):
    if abs(b) < 1e-9:
        return f"{a:.0f}px"
    return f"({a:.1f}px + {b:.4f} * ({COL}))"


def fit(rows):
    lines = [(a + PAD, b) for a, b in seg_envelope(rows)]
    formula = (css_line(*lines[0]) if len(lines) == 1
               else "max(" + ", ".join(css_line(*l) for l in lines) + ")")

    def value(w):                      # inside the column, COL == frame width
        return max(a + b * w for a, b in lines)
    slack = [(w, value(w) - h) for w, h in rows]
    worst_over = min(s for _, s in slack)
    worst_gap = max(s for _, s in slack)
    return formula, worst_over, worst_gap


def main():
    data = json.load(open("dev/heights.json"))
    out = []
    for fig in (1, 2, 3):
        formula, over, gap = fit(data[f"fig{fig}"])
        assert over >= 0, f"fig{fig} underfits by {over:.0f}px"
        style = f"display:block; width:100%; border:0; height:calc({formula});"
        out.append(
            f"Figure {fig}  (slack 0..{gap:.0f}px across 320-780, absorbed by fill):\n"
            f'[iframe src="https://REPLACE-ME.vercel.app/?fig={fig}" '
            f'title="Pantanal figure {fig}" loading="lazy" scrolling="auto" '
            f'style="{style}"][/iframe]\n')
        print(out[-1])
    open("dev/shortcodes.txt", "w").write("\n".join(out))


if __name__ == "__main__":
    main()
