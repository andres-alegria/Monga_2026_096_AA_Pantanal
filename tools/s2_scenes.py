#!/usr/bin/env python3
"""Pick the best (lowest-cloud) Sentinel-2 L2A scene per MGRS tile over the
Pantanal AOI from the Earth Search STAC and write their asset URLs to
data/s2/scenes.json. Stdlib only.

Usage: python3 tools/s2_scenes.py <datetime-range> <out.json>
e.g.   python3 tools/s2_scenes.py 2020-09-05T00:00:00Z/2020-09-25T23:59:59Z data/s2/scenes_sep.json
"""
import json
import sys
import urllib.request

API = "https://earth-search.aws.element84.com/v1/search"
BBOX = [-60.8, -22.4, -54.2, -14.8]   # map AOI — adjust here
ASSETS = ["visual", "green", "swir16", "scl"]

def search(dt):
    feats, body = [], {
        "collections": ["sentinel-2-l2a"],
        "bbox": BBOX,
        "datetime": dt,
        "query": {"eo:cloud_cover": {"lt": 40}},
        "limit": 100,
    }
    nxt = None
    while True:
        if nxt:
            body["next"] = nxt
        req = urllib.request.Request(
            API, json.dumps(body).encode(), {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.load(r)
        feats += d["features"]
        nxt = next((l.get("body", {}).get("next") for l in d.get("links", [])
                    if l.get("rel") == "next"), None)
        if not nxt:
            break
    return feats

def main():
    dt, out = sys.argv[1], sys.argv[2]
    mode = sys.argv[3] if len(sys.argv) > 3 else "best"
    feats = search(dt)
    chosen = []
    if mode == "fill":
        # per tile: one scene per date (newest baseline), then take scenes by
        # ascending nodata until the tile is covered — fills swath edges
        bydate = {}
        for f in feats:
            p = f["properties"]
            key = (p.get("grid:code"), p["datetime"][:10])
            bl = float(p.get("s2:processing_baseline", "0") or 0)
            if key not in bydate or bl > bydate[key][0]:
                bydate[key] = (bl, f)
        tiles = {}
        for (tile, _), (_, f) in bydate.items():
            tiles.setdefault(tile, []).append(f)
        for tile, fs in tiles.items():
            fs.sort(key=lambda f: f["properties"].get("s2:nodata_pixel_percentage", 100))
            cover, keep = 0.0, []
            for f in fs:
                keep.append(f)
                cover += 100 - f["properties"].get("s2:nodata_pixel_percentage", 100)
                if cover >= 105 or len(keep) == 3:
                    break
            chosen += keep
        # cloudiest first, so the clearest paints last in the mosaic
        chosen.sort(key=lambda f: -f["properties"].get("eo:cloud_cover", 100))
    else:
        best = {}
        for f in feats:
            p = f["properties"]
            tile = p.get("grid:code")
            cc = p.get("eo:cloud_cover", 100)
            # prefer lower cloud; tie-break on newer processing baseline
            key = (cc, -float(p.get("s2:processing_baseline", "0") or 0))
            if tile not in best or key < best[tile][0]:
                best[tile] = (key, f)
        chosen = [f for _, f in sorted((t, f) for t, (_, f) in best.items())]
    scenes = []
    for f in chosen:
        p = f["properties"]
        scenes.append({
            "id": f["id"],
            "tile": p.get("grid:code"),
            "date": p["datetime"][:10],
            "cloud": p.get("eo:cloud_cover"),
            "baseline": p.get("s2:processing_baseline"),
            "offset_applied": p.get("earthsearch:boa_offset_applied", False),
            "assets": {a: f["assets"][a]["href"] for a in ASSETS if a in f["assets"]},
        })
    with open(out, "w") as fh:
        json.dump(scenes, fh, indent=1)
    dates = sorted({s["date"] for s in scenes})
    print(f"{len(scenes)} tiles -> {out}; dates {dates[0]}..{dates[-1]}; "
          f"max cloud {max(s['cloud'] for s in scenes):.1f}%; "
          f"offsets applied: {sum(1 for s in scenes if s['offset_applied'])}/{len(scenes)}")

if __name__ == "__main__":
    main()
