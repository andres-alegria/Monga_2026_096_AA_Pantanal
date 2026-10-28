#!/usr/bin/env python3
"""Render the Fig 3 GBIF record maps: the muted June-2020 Sentinel-2
basemap (same treatment as the Fig 2 map) + occurrence-density cells as
record-yellow dots. One SVG per class; the first map carries the shared
scale bar for the row.

Run with QGIS's bundled python:
  .../python tools/render_gbif_maps.py data/s2/jun2020_visual.tif assets
"""
import base64
import csv
import math
import sys
import numpy as np
from osgeo import gdal

gdal.UseExceptions()

BBOX = (-60.8, -22.4, -54.2, -14.8)   # keep in sync with s2_mosaic.py
RES = 0.005                           # half the mosaic grid: 1320x1520
CLASSES = ["amphibia", "mammalia", "aves"]

# ---- style knobs — adjust here ----
DESAT = 0.55          # match render_fire_map.py
GAMMA = 1.6
DOT_RGB = (232, 166, 67)  # tiger-orange #e8a643 — matches the record pills
DOT_A = 0.92
DOT_R = 4                 # dot radius in px — adjust here
INK = "#fcfcfc"
COUNTRY_INK = "#fcfcfc"   # country borders + labels — adjust here
FILL_RGB = (143, 208, 205)  # ecoregion fill, flood teal #8fd0cd — adjust here
FILL_A = 0.5                # ecoregion fill opacity — adjust here
FS = 44                   # scale-bar font size — adjust here
FS_COUNTRY = 40           # country-label font size — adjust here

NE = ("/Users/andres/Documents/_GIS/Natural Earth/10m_cultural/"
      "ne_10m_admin_0_boundary_lines_land.shp")
COUNTRIES = [  # lon, lat — all caps per the system's cartography rule
    (-55.75, -15.45, "BRAZIL"),
    (-60.45, -18.60, "BOLIVIA"),
    (-58.6, -21.9, "PARAGUAY"),
]


def main():
    vis_tif, outdir = sys.argv[1:3]
    vis = gdal.Open(vis_tif).ReadAsArray().astype(np.float32)[:, ::2, ::2]
    _, H, W = vis.shape

    lum = vis[0] * 0.299 + vis[1] * 0.587 + vis[2] * 0.114
    base = vis * (1 - DESAT) + lum[None] * DESAT
    base = 255.0 * np.power(np.clip(base, 0, 255) / 255.0, 1.0 / GAMMA)

    yy, xx = np.mgrid[-DOT_R:DOT_R + 1, -DOT_R:DOT_R + 1]
    disk = (yy ** 2 + xx ** 2) <= DOT_R ** 2

    import gbif_fetch
    from osgeo import ogr, osr
    poly = gbif_fetch.load_polygon()

    # country borders from Natural Earth, clipped to the AOI
    bds = ogr.Open(NE)
    blyr = bds.GetLayer()
    blyr.SetSpatialFilterRect(BBOX[0], BBOX[1], BBOX[2], BBOX[3])
    border_paths = []
    for feat in blyr:
        geom = feat.GetGeometryRef()
        lines = [geom] if geom.GetGeometryName() == "LINESTRING" else \
                [geom.GetGeometryRef(i) for i in range(geom.GetGeometryCount())]
        for ln in lines:
            bpts = [((ln.GetX(i) - BBOX[0]) / RES, (BBOX[3] - ln.GetY(i)) / RES)
                    for i in range(ln.GetPointCount())]
            if len(bpts) > 1:
                border_paths.append(
                    "M" + " L".join(f"{x:.0f},{y:.0f}" for x, y in bpts))

    # translucent teal ecoregion fill (matches the original video's water
    # layer register), burned in UNDER the dots
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

    km100 = 100 / (111.32 * math.cos(math.radians((BBOX[1] + BBOX[3]) / 2))) / RES
    sx, sy = 45, H - 55

    for ci, name in enumerate(CLASSES):
        dots = np.zeros((H, W), bool)
        with open(f"data/gbif/{name}.csv", newline="") as fh:
            for row in csv.DictReader(fh):
                x = int((float(row["longitude"]) - BBOX[0]) / RES)
                y = int((BBOX[3] - float(row["latitude"])) / RES)
                y0, y1 = max(0, y - DOT_R), min(H, y + DOT_R + 1)
                x0, x1 = max(0, x - DOT_R), min(W, x + DOT_R + 1)
                dots[y0:y1, x0:x1] |= disk[y0 - (y - DOT_R):disk.shape[0] - ((y + DOT_R + 1) - y1),
                                           x0 - (x - DOT_R):disk.shape[1] - ((x + DOT_R + 1) - x1)]
        img = base.copy()
        for b in range(3):
            img[b][dots] = img[b][dots] * (1 - DOT_A) + DOT_RGB[b] * DOT_A
        img = np.clip(img, 0, 255).astype(np.uint8)

        mds = gdal.GetDriverByName("MEM").Create("", W, H, 3, gdal.GDT_Byte)
        for b in range(3):
            mds.GetRasterBand(b + 1).WriteArray(img[b])
        jpath = f"{outdir}/gbif_{name}_s2.jpg"
        gdal.GetDriverByName("JPEG").CreateCopy(jpath, mds, options=["QUALITY=88"])
        b64 = base64.b64encode(open(jpath, "rb").read()).decode()

        svg = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {W} {H}" font-family="Public Sans, Helvetica, sans-serif">',
               f'<image href="data:image/jpeg;base64,{b64}" x="0" y="0" width="{W}" height="{H}"/>',
               f'<g fill="none" stroke="{COUNTRY_INK}" stroke-width="2" opacity="0.6">'
               + "".join(f'<path d="{d}"/>' for d in border_paths) + '</g>']
        for lon, lat, cname in COUNTRIES:
            cx = (lon - BBOX[0]) / RES
            cy = (BBOX[3] - lat) / RES
            svg.append(f'<text x="{cx:.0f}" y="{cy:.0f}" font-size="{FS_COUNTRY}" '
                       f'fill="{COUNTRY_INK}" opacity="0.8" letter-spacing="5">{cname}</text>')
        if ci == 0:   # shared scale bar on the row's first map
            svg.append(f'<g stroke="{INK}" stroke-width="4">'
                       f'<line x1="{sx}" y1="{sy}" x2="{sx + km100:.0f}" y2="{sy}"/>'
                       f'<line x1="{sx}" y1="{sy - 10}" x2="{sx}" y2="{sy + 10}"/>'
                       f'<line x1="{sx + km100:.0f}" y1="{sy - 10}" x2="{sx + km100:.0f}" y2="{sy + 10}"/></g>')
            svg.append(f'<text x="{sx:.0f}" y="{sy - 20}" font-size="{FS}" fill="{INK}" text-anchor="middle" opacity="0.95">0</text>')
            svg.append(f'<text x="{sx + km100:.0f}" y="{sy - 20}" font-size="{FS}" fill="{INK}" text-anchor="middle" opacity="0.95">100 km</text>')
        svg.append('</svg>')
        spath = f"{outdir}/gbif_{name}_s2.svg"
        open(spath, "w").write("\n".join(svg))
        print(f"wrote {spath} ({W}x{H}); dot px {int(dots.sum())}")


if __name__ == "__main__":
    main()
