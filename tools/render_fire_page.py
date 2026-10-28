#!/usr/bin/env python3
"""Build the Fig 2 page assets that replace the burned-in video:

  assets/fig2_basemap.jpg  — muted June-2020 Sentinel-2 basemap + translucent
                             teal Pantanal ecoregion + white borders, country
                             and city labels, scale bar (all burned in)
  assets/fire_days.js      — VIIRS detections as per-day cell lists on a
                             660x760 grid (0.01 deg), base-36 packed, for the
                             canvas animation in js/main.js

Run with QGIS's bundled python:
  .../python tools/render_fire_page.py data/s2/jun2020_visual.tif \
      data/firms/fires_aoi_2020.csv assets
"""
import csv
import datetime
import json
import math
import sys
import numpy as np
from osgeo import gdal, ogr, osr

gdal.UseExceptions()

BBOX = (-60.8, -22.4, -54.2, -14.8)   # keep in sync with s2_mosaic.py
RES = 0.005                           # basemap grid: 1320x1520
CELL = 0.01                           # fire-cell grid: 660x760

# ---- style knobs — adjust here ----
DESAT = 0.55
GAMMA = 1.6
FILL_RGB = (143, 208, 205)  # ecoregion fill, flood teal #8fd0cd
FILL_A = 0.5
INK = "#fcfcfc"

LABELS = [  # lon, lat, text, kind
    (-57.95, -16.55, "BRAZIL", "country"),
    (-60.3, -18.3, "BOLIVIA", "country"),
    (-59.1, -21.5, "PARAGUAY", "country"),
    (-56.097, -15.601, "Cuiabá", "city"),
    (-54.646, -20.469, "Campo Grande", "city"),
]
FS_COUNTRY = 34
FS = 30
NE = ("/Users/andres/Documents/_GIS/Natural Earth/10m_cultural/"
     "ne_10m_admin_0_boundary_lines_land.shp")


def b36(n):
    s = ""
    while True:
        n, r = divmod(n, 36)
        s = "0123456789abcdefghijklmnopqrstuvwxyz"[r] + s
        if n == 0:
            return s


def main():
    vis_tif, fires_csv, outdir = sys.argv[1:4]
    sys.path.insert(0, "tools")
    import gbif_fetch

    vis = gdal.Open(vis_tif).ReadAsArray().astype(np.float32)[:, ::2, ::2]
    _, H, W = vis.shape
    lum = vis[0] * 0.299 + vis[1] * 0.587 + vis[2] * 0.114
    base = vis * (1 - DESAT) + lum[None] * DESAT
    base = 255.0 * np.power(np.clip(base, 0, 255) / 255.0, 1.0 / GAMMA)

    # teal ecoregion fill
    poly = gbif_fetch.load_polygon()
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    vds = ogr.GetDriverByName("MEM").CreateDataSource("")
    vlyr = vds.CreateLayer("p", srs)
    f = ogr.Feature(vlyr.GetLayerDefn())
    f.SetGeometry(poly)
    vlyr.CreateFeature(f)
    rds = gdal.GetDriverByName("MEM").Create("", W, H, 1, gdal.GDT_Byte)
    rds.SetGeoTransform((BBOX[0], RES, 0, BBOX[3], 0, -RES))
    rds.SetProjection(srs.ExportToWkt())
    gdal.RasterizeLayer(rds, [1], vlyr, burn_values=[1])
    inside = rds.GetRasterBand(1).ReadAsArray().astype(bool)
    for b in range(3):
        base[b][inside] = base[b][inside] * (1 - FILL_A) + FILL_RGB[b] * FILL_A
    img = np.clip(base, 0, 255).astype(np.uint8)

    # photo layer as JPEG; furniture goes in a separate transparent SVG that
    # the page stacks ABOVE the fire canvas, so labels stay legible over red
    mds = gdal.GetDriverByName("MEM").Create("", W, H, 3, gdal.GDT_Byte)
    for b in range(3):
        mds.GetRasterBand(b + 1).WriteArray(img[b])
    jpath = f"{outdir}/fig2_basemap_photo.jpg"
    gdal.GetDriverByName("JPEG").CreateCopy(jpath, mds, options=["QUALITY=88"])

    def px(lon, lat):
        return (lon - BBOX[0]) / RES, (BBOX[3] - lat) / RES

    paths = []
    ds = ogr.Open(NE)
    lyr = ds.GetLayer()
    lyr.SetSpatialFilterRect(BBOX[0], BBOX[1], BBOX[2], BBOX[3])
    for feat in lyr:
        geom = feat.GetGeometryRef()
        lines = [geom] if geom.GetGeometryName() == "LINESTRING" else \
                [geom.GetGeometryRef(i) for i in range(geom.GetGeometryCount())]
        for ln in lines:
            pts = [px(ln.GetX(i), ln.GetY(i)) for i in range(ln.GetPointCount())]
            if len(pts) > 1:
                paths.append("M" + " L".join(f"{x:.0f},{y:.0f}" for x, y in pts))

    km100 = 100 / (111.32 * math.cos(math.radians((BBOX[1] + BBOX[3]) / 2))) / RES
    sx, sy = 45, H - 55

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="Public Sans, Helvetica, sans-serif">',
           f'<g fill="none" stroke="{INK}" stroke-width="2" opacity="0.6">'
           + "".join(f'<path d="{d}"/>' for d in paths) + '</g>']
    for lon, lat, text, kind in LABELS:
        x, y = px(lon, lat)
        if kind == "city":
            svg.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="4" fill="{INK}"/>')
            if x + 10 + FS * 0.55 * len(text) > W - 14:
                svg.append(f'<text x="{x - 10:.0f}" y="{y - 8:.0f}" font-size="{FS}" fill="{INK}" text-anchor="end" opacity="0.95">{text}</text>')
            else:
                svg.append(f'<text x="{x + 10:.0f}" y="{y - 8:.0f}" font-size="{FS}" fill="{INK}" opacity="0.95">{text}</text>')
        else:
            svg.append(f'<text x="{x:.0f}" y="{y:.0f}" font-size="{FS_COUNTRY}" fill="{INK}" opacity="0.8" letter-spacing="4">{text}</text>')
    svg.append(f'<g stroke="{INK}" stroke-width="3">'
               f'<line x1="{sx}" y1="{sy}" x2="{sx + km100:.0f}" y2="{sy}"/>'
               f'<line x1="{sx}" y1="{sy - 8}" x2="{sx}" y2="{sy + 8}"/>'
               f'<line x1="{sx + km100:.0f}" y1="{sy - 8}" x2="{sx + km100:.0f}" y2="{sy + 8}"/></g>')
    svg.append(f'<text x="{sx}" y="{sy - 16}" font-size="{FS}" fill="{INK}" text-anchor="middle" opacity="0.95">0</text>')
    svg.append(f'<text x="{sx + km100:.0f}" y="{sy - 16}" font-size="{FS}" fill="{INK}" text-anchor="middle" opacity="0.95">100 km</text>')
    svg.append('</svg>')
    open(f"{outdir}/fig2_overlay.svg", "w").write("\n".join(svg))

    # ---- fire detections -> per-day new cells on the CELL grid ----
    gw = round((BBOX[2] - BBOX[0]) / CELL)
    gh = round((BBOX[3] - BBOX[1]) / CELL)
    first = {}
    n = 0
    with open(fires_csv, newline="") as fh:
        for row in csv.DictReader(fh):
            lon, lat = float(row["longitude"]), float(row["latitude"])
            cx = min(int((lon - BBOX[0]) / CELL), gw - 1)
            cy = min(int((BBOX[3] - lat) / CELL), gh - 1)
            d = datetime.date.fromisoformat(row["acq_date"]).timetuple().tm_yday
            idx = cy * gw + cx
            if idx not in first or d < first[idx]:
                first[idx] = d
            n += 1
    days = {}
    for idx, d in first.items():
        days.setdefault(d, []).append(idx)
    packed = {d: ",".join(b36(i) for i in sorted(v)) for d, v in sorted(days.items())}
    out = f"{outdir}/fire_days.js"
    with open(out, "w") as fh:
        fh.write("// VIIRS S-NPP 2020 detections (>= nominal confidence) as first-\n")
        fh.write("// detection day per 0.01-degree cell; indices base-36, row-major\n")
        fh.write("window.FIRE_DAYS = ")
        json.dump({"w": gw, "h": gh, "days": packed}, fh, separators=(",", ":"))
        fh.write(";\n")
    import os
    print(f"basemap {W}x{H}; {n} detections -> {len(first)} cells, "
          f"{len(packed)} days; fire_days.js {os.path.getsize(out)//1024} KB")


if __name__ == "__main__":
    main()
