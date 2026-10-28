#!/usr/bin/env python3
"""Fetch GBIF occurrence density + counts for the Fig 3 record maps.

For each vertebrate class: the v2 maps-API density tiles (MVT, EPSG:3857,
z7 — ~610 m cells) clipped to the map AOI -> data/gbif/<class>.csv
(lon,lat,total), plus record and distinct-species counts from the search
API -> data/gbif/counts.json.

Run with QGIS's bundled python (GDAL decodes the MVT tiles):
  PROJ_DATA=... GDAL_DATA=... .../python tools/gbif_fetch.py
"""
import json
import math
import os
import time
import urllib.request
import urllib.parse
from osgeo import gdal, ogr, osr

gdal.UseExceptions()

BBOX = (-60.8, -22.4, -54.2, -14.8)   # keep in sync with s2_mosaic.py
RES = 0.0025
Z = 7                                  # density tile zoom — adjust here
CLASSES = {"amphibia": 131, "mammalia": 359, "aves": 212}
OUT = "data/gbif"
# records are limited to the WWF (2001) Pantanal ecoregion — the IBGE biome
# border used first covers only the Brazilian portion
SHP = ("/Users/andres/Documents/_GIS/WWF_Ecoregions (2001)/"
       "wwf_terr_ecos.shp")


def load_polygon():
    """Pantanal ecoregion (all parts dissolved) in EPSG:4326 (lon,lat)."""
    ds = ogr.Open(SHP)
    lyr = ds.GetLayer()
    lyr.SetAttributeFilter("ECO_NAME = 'Pantanal'")
    coll = ogr.Geometry(ogr.wkbMultiPolygon)
    for feat in lyr:
        coll.AddGeometry(feat.GetGeometryRef().Clone())
    g = coll.UnionCascaded()
    src = lyr.GetSpatialRef()
    src.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    dst = osr.SpatialReference()
    dst.ImportFromEPSG(4326)
    dst.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    g.Transform(osr.CoordinateTransformation(src, dst))
    return g


def _parts(g):
    if g.GetGeometryName() == "POLYGON":
        return [g]
    return [g.GetGeometryRef(i) for i in range(g.GetGeometryCount())]


def polygon_wkt(g, max_chars=2900):
    """Simplified CCW WKT that fits in a GET URL (GBIF's front end 400s
    somewhere past ~4 kB of URL, so stay well under)."""
    tol = 0.01
    while True:
        s = g.SimplifyPreserveTopology(tol)
        rings = []
        for p in _parts(s):
            ring = p.GetGeometryRef(0)
            pts = [(ring.GetX(i), ring.GetY(i))
                   for i in range(ring.GetPointCount())]
            if len(pts) < 4:
                continue
            area2 = sum(x0 * y1 - x1 * y0
                        for (x0, y0), (x1, y1) in zip(pts, pts[1:]))
            if area2 < 0:   # clockwise -> reverse
                pts.reverse()
            rings.append("((" +
                         ",".join(f"{x:.3f} {y:.3f}" for x, y in pts) + "))")
        wkt = ("POLYGON" + rings[0] if len(rings) == 1
               else "MULTIPOLYGON(" + ",".join(rings) + ")")
        if len(wkt) <= max_chars:
            return wkt, tol
        tol *= 1.3


def polygon_mask(wkt):
    """Rasterize the (same, simplified) polygon onto the mosaic grid."""
    import numpy as np
    W = round((BBOX[2] - BBOX[0]) / RES)
    H = round((BBOX[3] - BBOX[1]) / RES)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    vds = ogr.GetDriverByName("Memory").CreateDataSource("")
    vlyr = vds.CreateLayer("p", srs)
    f = ogr.Feature(vlyr.GetLayerDefn())
    f.SetGeometry(ogr.CreateGeometryFromWkt(wkt))
    vlyr.CreateFeature(f)
    rds = gdal.GetDriverByName("MEM").Create("", W, H, 1, gdal.GDT_Byte)
    rds.SetGeoTransform((BBOX[0], RES, 0, BBOX[3], 0, -RES))
    rds.SetProjection(srs.ExportToWkt())
    gdal.RasterizeLayer(rds, [1], vlyr, burn_values=[1])
    return rds.GetRasterBand(1).ReadAsArray(), W, H


def tile_range():
    n = 2 ** Z
    xs = [int((lon + 180) / 360 * n) for lon in (BBOX[0], BBOX[2])]
    ys = []
    for lat in (BBOX[3], BBOX[1]):   # N first: y grows southward
        r = math.radians(lat)
        ys.append(int((1 - math.asinh(math.tan(r)) / math.pi) / 2 * n))
    return range(xs[0], xs[1] + 1), range(ys[0], ys[1] + 1)


def get(url, timeout=60, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "monga-2026-096"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(3 * (i + 1))


def fetch(url, path):
    data = get(url)
    open(path, "wb").write(data)
    return len(data)


def main():
    os.makedirs(OUT, exist_ok=True)
    t3857 = osr.SpatialReference(); t3857.ImportFromEPSG(3857)
    t4326 = osr.SpatialReference(); t4326.ImportFromEPSG(4326)
    t4326.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    tr = osr.CoordinateTransformation(t3857, t4326)

    # dots cover the whole map bbox (the road pattern reads beyond the biome);
    # the pill counts are queried inside the biome polygon only
    GEOM, tol = polygon_wkt(load_polygon())
    print(f"biome polygon: WKT {len(GEOM)} chars (tol {tol}deg)", flush=True)

    counts = {}
    xs, ys = tile_range()
    for name, key in CLASSES.items():
        rows = []
        for x in xs:
            for y in ys:
                url = (f"https://api.gbif.org/v2/map/occurrence/density/"
                       f"{Z}/{x}/{y}.mvt?srs=EPSG%3A3857&taxonKey={key}")
                tmp = f"{OUT}/tile_{key}_{x}_{y}.mvt"
                try:
                    n = fetch(url, tmp)
                except Exception as e:
                    print("FAIL", name, x, y, e, flush=True)
                    continue
                if n == 0:
                    os.remove(tmp)
                    continue
                ds = gdal.OpenEx(tmp, gdal.OF_VECTOR,
                                 open_options=[f"X={x}", f"Y={y}", f"Z={Z}"])
                lyr = ds.GetLayer(0)
                for f in lyr:
                    g = f.GetGeometryRef().Clone()
                    g.Transform(tr)
                    lon, lat = g.GetX(), g.GetY()
                    if BBOX[0] <= lon <= BBOX[2] and BBOX[1] <= lat <= BBOX[3]:
                        rows.append((lon, lat, f["total"]))
                ds = None
                os.remove(tmp)
                time.sleep(0.2)
        with open(f"{OUT}/{name}.csv", "w") as fh:
            fh.write("longitude,latitude,total\n")
            for lon, lat, tot in rows:
                fh.write(f"{lon:.5f},{lat:.5f},{tot}\n")
        print(f"{name}: {len(rows)} cells, {sum(r[2] for r in rows)} records on map",
              flush=True)

        # record + species counts from the search API (same AOI)
        q = urllib.parse.urlencode({
            "geometry": GEOM, "taxonKey": key, "hasCoordinate": "true",
            "hasGeospatialIssue": "false", "occurrenceStatus": "PRESENT",
            "limit": 0, "facet": "speciesKey", "facetLimit": 8000})
        try:
            d = json.loads(get(
                "https://api.gbif.org/v1/occurrence/search?" + q, timeout=120))
            counts[name] = {"records": d["count"],
                            "species": len(d["facets"][0]["counts"])}
        except Exception as e:   # GBIF flakes — keep the previous counts
            old = json.load(open(f"{OUT}/counts.json"))
            counts[name] = old[name]
            counts[name]["stale"] = True
            print(f"counts query failed for {name} ({e}); kept previous",
                  flush=True)
        print(name, counts[name], flush=True)
        time.sleep(1)

    counts["fetched"] = time.strftime("%Y-%m-%d")
    json.dump(counts, open(f"{OUT}/counts.json", "w"), indent=1)


if __name__ == "__main__":
    main()
