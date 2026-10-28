#!/usr/bin/env python3
"""Compose the rebuilt Figure-2 map: muted Sentinel-2 basemap + MNDWI water
in flood teal + VIIRS detections in fire red, wrapped in an SVG with
editable furniture (borders, labels, scale bar) in Mongabay tokens.

Run with QGIS's bundled python (GDAL + numpy):
  .../python tools/render_fire_map.py <visual.tif> <water.tif> \
      data/firms/fires_aoi_to_sep25.csv <out.svg>
Also writes <out>.preview.jpg for a quick look.
"""
import base64
import csv
import sys
import numpy as np
from osgeo import gdal, ogr

gdal.UseExceptions()

BBOX = (-60.8, -22.4, -54.2, -14.8)   # keep in sync with s2_mosaic.py
RES = 0.0025

# ---- style knobs — adjust here ----
DESAT = 0.55          # basemap desaturation (0 = original colors, 1 = gray)
DARKEN = 1.0          # basemap brightness factor
GAMMA = 1.6           # midtone lift (1 = none) — raw S2 true color is dark
WATER_RGB = (143, 208, 205)   # flood teal #8fd0cd
WATER_A = 0.85
FIRE_RGB = (160, 19, 19)      # fire red #a01313
FIRE_A = 0.92
BORDER = "#ffffff"
INK = "#fcfcfc"

NE = "/Users/andres/Documents/_GIS/Natural Earth/10m_cultural/ne_10m_admin_0_boundary_lines_land.shp"

LABELS = [  # lon, lat, text, kind — countries fully spelled, all caps
    (-57.95, -16.55, "BRAZIL", "country"),
    (-60.3, -18.3, "BOLIVIA", "country"),
    (-59.6, -21.9, "PARAGUAY", "country"),
    (-56.097, -15.601, "Cuiabá", "city"),
    (-54.646, -20.469, "Campo Grande", "city"),
]


def px(lon, lat):
    return (lon - BBOX[0]) / RES, (BBOX[3] - lat) / RES


def main():
    vis_tif, water_tif, fires_csv, out_svg = sys.argv[1:5]
    vis = gdal.Open(vis_tif).ReadAsArray().astype(np.float32)
    water = gdal.Open(water_tif).ReadAsArray()
    _, H, W = vis.shape

    # despeckle the water mask: keep pixels with at least 2 wet neighbours
    nb = np.zeros_like(water, np.uint8)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            nb[max(0, dy):H - max(0, -dy), max(0, dx):W - max(0, -dx)] += \
                water[max(0, -dy):H - max(0, dy), max(0, -dx):W - max(0, dx)]
    water = (water == 1) & (nb >= 2)

    # muted basemap
    lum = vis[0] * 0.299 + vis[1] * 0.587 + vis[2] * 0.114
    img = (vis * (1 - DESAT) + lum[None] * DESAT) * DARKEN
    img = 255.0 * np.power(np.clip(img, 0, 255) / 255.0, 1.0 / GAMMA)

    # water overlay
    for b in range(3):
        img[b][water] = img[b][water] * (1 - WATER_A) + WATER_RGB[b] * WATER_A

    # fire detections -> 2x2 blocks on the grid
    fire = np.zeros((H, W), bool)
    with open(fires_csv, newline="") as fh:
        for row in csv.DictReader(fh):
            x, y = px(float(row["longitude"]), float(row["latitude"]))
            xi, yi = int(x), int(y)
            fire[max(0, yi - 1):yi + 1, max(0, xi - 1):xi + 1] = True
    n_fire_cells = int(fire.sum())
    for b in range(3):
        img[b][fire] = img[b][fire] * (1 - FIRE_A) + FIRE_RGB[b] * FIRE_A

    img = np.clip(img, 0, 255).astype(np.uint8)

    # ---- write composite as JPEG, embed in SVG ----
    drv = gdal.GetDriverByName("MEM")
    mds = drv.Create("", W, H, 3, gdal.GDT_Byte)
    for b in range(3):
        mds.GetRasterBand(b + 1).WriteArray(img[b])
    jpath = out_svg + ".preview.jpg"
    gdal.GetDriverByName("JPEG").CreateCopy(jpath, mds, options=["QUALITY=88"])
    b64 = base64.b64encode(open(jpath, "rb").read()).decode()

    # borders from Natural Earth, clipped to the AOI
    paths = []
    ds = ogr.Open(NE)
    lyr = ds.GetLayer()
    lyr.SetSpatialFilterRect(*[BBOX[i] for i in (0, 1, 2, 3)])
    for feat in lyr:
        geom = feat.GetGeometryRef()
        lines = [geom] if geom.GetGeometryName() == "LINESTRING" else \
                [geom.GetGeometryRef(i) for i in range(geom.GetGeometryCount())]
        for ln in lines:
            pts = [px(ln.GetX(i), ln.GetY(i)) for i in range(ln.GetPointCount())]
            if len(pts) > 1:
                paths.append("M" + " L".join(f"{x:.0f},{y:.0f}" for x, y in pts))

    # scale bar: 100 km at centre latitude
    import math
    km100 = 100 / (111.32 * math.cos(math.radians((BBOX[1] + BBOX[3]) / 2))) / RES
    sx, sy = 90, H - 110
    FS = 56  # ≈ 11 px at the figure's display width — adjust here

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {W} {H}" font-family="Public Sans, Helvetica, sans-serif">')
    svg.append(f'<image href="data:image/jpeg;base64,{b64}" x="0" y="0" width="{W}" height="{H}"/>')
    svg.append(f'<g fill="none" stroke="{BORDER}" stroke-width="3.5" opacity="0.65">')
    svg.extend(f'<path d="{d}"/>' for d in paths)
    svg.append('</g>')
    for lon, lat, text, kind in LABELS:
        x, y = px(lon, lat)
        if kind == "city":
            svg.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="7" fill="{INK}"/>')
            # flip the label to the left of the dot when it would clip the edge
            if x + 16 + FS * 0.55 * len(text) > W - 20:
                svg.append(f'<text x="{x - 16:.0f}" y="{y - 12:.0f}" font-size="{FS}" fill="{INK}" text-anchor="end" opacity="0.95">{text}</text>')
            else:
                svg.append(f'<text x="{x + 16:.0f}" y="{y - 12:.0f}" font-size="{FS}" fill="{INK}" opacity="0.95">{text}</text>')
        else:
            svg.append(f'<text x="{x:.0f}" y="{y:.0f}" font-size="{FS}" fill="{INK}" opacity="0.8" letter-spacing="6">{text}</text>')
    # scale bar
    svg.append(f'<g stroke="{INK}" stroke-width="5">'
               f'<line x1="{sx}" y1="{sy}" x2="{sx + km100:.0f}" y2="{sy}"/>'
               f'<line x1="{sx}" y1="{sy - 12}" x2="{sx}" y2="{sy + 12}"/>'
               f'<line x1="{sx + km100 / 2:.0f}" y1="{sy - 9}" x2="{sx + km100 / 2:.0f}" y2="{sy + 9}"/>'
               f'<line x1="{sx + km100:.0f}" y1="{sy - 12}" x2="{sx + km100:.0f}" y2="{sy + 12}"/></g>')
    for v, dx in ((0, 0), (50, km100 / 2), (100, km100)):
        anchor = "middle"
        svg.append(f'<text x="{sx + dx:.0f}" y="{sy - 26}" font-size="{FS}" fill="{INK}" text-anchor="{anchor}" opacity="0.95">{v}{" km" if v == 100 else ""}</text>')
    svg.append('</svg>')
    open(out_svg, "w").write("\n".join(svg))
    print(f"wrote {out_svg} ({W}x{H}); fire cells {n_fire_cells}; water px {int(water.sum())}")


if __name__ == "__main__":
    main()
