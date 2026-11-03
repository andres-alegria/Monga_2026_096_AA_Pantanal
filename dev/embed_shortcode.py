#!/usr/bin/env python3
"""Emit the [iframe] shortcodes for the scaled embeds -> dev/shortcodes.txt.

Each solo figure renders its full 1060px two-column design and scales to
the frame width (like a static figure), so its height is one straight
line of the column width: H_design * COL / 1060. No breakpoints, no
scrollbar bands. Design heights come from dev/heights.json — re-measure
with dev/measure.html after ANY copy or layout change.
"""
import json

DOMAIN = "https://monga2026096aapantanal.vercel.app"
DESIGN_W = 1060
PAD = 6      # rounding + late-font allowance; spare px sit as a hairline gap

TITLES = {
    1: "Dry and wet season dynamics in the Pantanal",
    2: "In 2020 the water stayed away, and fire moved in",
    3: "Why scientists are wiring the wetland for sound",
}


def main():
    heights = json.load(open("dev/heights.json"))
    out = []
    for fig in (1, 2, 3):
        h = heights[f"fig{fig}"]
        # the scaled embed is strictly proportional, so the frame can size
        # itself from its own real width — no column-width assumption
        style = (f"display:block; width:100%; height:auto; "
                 f"aspect-ratio:{DESIGN_W}/{h + PAD}; border:0;")
        out.append(
            f"Figure {fig}  (design {DESIGN_W}x{h}px, scaled to the column):\n"
            f'[iframe src="{DOMAIN}/?fig={fig}" '
            f'title="{TITLES[fig]}" loading="lazy" scrolling="no" '
            f'style="{style}"][/iframe]\n')
        print(out[-1])
    open("dev/shortcodes.txt", "w").write("\n".join(out))


if __name__ == "__main__":
    main()
