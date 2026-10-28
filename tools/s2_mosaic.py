#!/usr/bin/env python3
"""Mosaic Sentinel-2 L2A over the Pantanal AOI: true-color basemap +
MNDWI water mask (SCL cloud/shadow-masked), from the scenes picked by
s2_scenes.py. Run with QGIS's bundled python (GDAL + numpy):

  PROJ_DATA=/Applications/QGIS.app/Contents/Resources/qgis/proj \
  GDAL_DATA=/Applications/QGIS.app/Contents/Resources/qgis/gdal \
  /Applications/QGIS.app/Contents/MacOS/bin/python3 tools/s2_mosaic.py \
      data/s2/scenes_sep.json data/s2/sep2020

Writes <prefix>_visual.tif (RGB uint8), <prefix>_water.tif (uint8 0/1)
and <prefix>_seen.tif (coverage diagnostic).
"""
import json
import sys
import numpy as np
from osgeo import gdal, osr

gdal.UseExceptions()

BBOX = (-60.8, -22.4, -54.2, -14.8)   # W, S, E, N — map AOI, adjust here
RES = 0.0025                          # ~275 m grid
MNDWI_T = 0.1                         # water threshold — adjust here
VOTE = 0.4                            # min fraction of clear looks that are wet
W = round((BBOX[2] - BBOX[0]) / RES)
H = round((BBOX[3] - BBOX[1]) / RES)


def warp(href, resample):
    opts = gdal.WarpOptions(
        format="MEM", dstSRS="EPSG:4326",
        outputBounds=BBOX, xRes=RES, yRes=RES,
        resampleAlg=resample, errorThreshold=0.125,
        warpMemoryLimit=256)
    return gdal.Warp("", "/vsicurl/" + href, options=opts)


def main():
    scenes = json.load(open(sys.argv[1]))
    prefix = sys.argv[2]
    mode = sys.argv[3] if len(sys.argv) > 3 else "both"   # visual | water | both
    vis = np.zeros((3, H, W), np.uint8)
    painted = np.zeros((H, W), np.uint8)   # visual: any pixel painted at all
    wcount = np.zeros((H, W), np.uint16)   # water: wet looks per pixel
    vcount = np.zeros((H, W), np.uint16)   # water: clear looks per pixel
    seen = np.zeros((H, W), np.uint8)

    for i, s in enumerate(scenes):
        try:
            scl = warp(s["assets"]["scl"], "near").ReadAsArray()
            if mode in ("water", "both"):
                g = warp(s["assets"]["green"], "bilinear").ReadAsArray().astype(np.float32)
                sw = warp(s["assets"]["swir16"], "bilinear").ReadAsArray().astype(np.float32)
            if mode in ("visual", "both"):
                v = warp(s["assets"]["visual"], "average").ReadAsArray()
        except Exception as e:
            print("FAIL", s["id"], e, flush=True)
            continue
        msg = ""
        cloudy = np.isin(scl, (3, 8, 9, 10))  # cloud shadow + clouds + cirrus
        if mode in ("water", "both"):
            off = 1000.0 if s.get("offset_applied") else 0.0
            g -= off
            sw -= off
            valid = (scl > 0) & (g > -900)
            denom = g + sw
            # g > 0 and a denominator floor: smoke-dead scenes come back with
            # negative reflectance and must not count as clear looks at all
            good = valid & ~cloudy & (g > 0) & (denom > 100)
            mndwi = np.divide(g - sw, denom, out=np.full_like(g, -1.0), where=denom > 0)
            # water = Sen2Cor's water class confirmed by MNDWI. A strong-MNDWI
            # escape hatch was tried and fired on fresh burn scars (dark in
            # green AND swir16) — real water here is scl==6 almost everywhere
            w_ = good & (scl == 6) & (mndwi > MNDWI_T)
            wcount[w_] += 1
            vcount[good] += 1
            seen[valid] = 1
            msg = f"water_px={int(w_.sum())}"
        if mode in ("visual", "both"):
            vmask = v.sum(axis=0) > 0
            clear = vmask & ~cloudy
            fallback = vmask & (painted == 0)  # cover holes even if cloudy
            for b in range(3):
                vis[b][fallback] = v[b][fallback]
                vis[b][clear] = v[b][clear]
            painted[vmask] = 1
            seen[vmask] = 1
        print(f"{i+1}/{len(scenes)} {s['id']} {msg}", flush=True)

    # majority vote: a pixel is water only if wet in >= VOTE of its clear looks
    water = ((wcount > 0) & (wcount >= VOTE * vcount)).astype(np.uint8)

    if mode in ("visual", "both") and (painted == 0).any():
        # inpaint the never-covered swath wedges from their surroundings
        mem = gdal.GetDriverByName("MEM")
        md = mem.Create("", W, H, 1, gdal.GDT_Byte)
        md.GetRasterBand(1).WriteArray(painted)
        for b in range(3):
            vb = mem.Create("", W, H, 1, gdal.GDT_Byte)
            vb.GetRasterBand(1).WriteArray(vis[b])
            gdal.FillNodata(vb.GetRasterBand(1), md.GetRasterBand(1), 150, 0)
            vis[b] = vb.GetRasterBand(1).ReadAsArray()
        print(f"inpainted {int((painted == 0).sum())} px", flush=True)

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    wkt = srs.ExportToWkt()
    gt = (BBOX[0], RES, 0, BBOX[3], 0, -RES)
    drv = gdal.GetDriverByName("GTiff")
    outs = [(prefix + "_seen.tif", seen[None])]
    if mode in ("visual", "both"):
        outs.append((prefix + "_visual.tif", vis))
    if mode in ("water", "both"):
        outs.append((prefix + "_water.tif", water[None]))
        # keep the raw counts so the water rule can be re-tuned offline
        outs.append((prefix + "_wcount.tif", np.clip(wcount, 0, 255).astype(np.uint8)[None]))
        outs.append((prefix + "_vcount.tif", np.clip(vcount, 0, 255).astype(np.uint8)[None]))
    for name, arr in outs:
        ds = drv.Create(name, W, H, arr.shape[0], gdal.GDT_Byte,
                        ["COMPRESS=DEFLATE", "PREDICTOR=2"])
        ds.SetGeoTransform(gt)
        ds.SetProjection(wkt)
        for b in range(arr.shape[0]):
            ds.GetRasterBand(b + 1).WriteArray(arr[b])
        ds.FlushCache()
    print("done:", prefix, f"grid {W}x{H}", f"water km2~{water.sum() * (RES*111.0)*(RES*111.0*np.cos(np.radians(18.6))):.0f}")


if __name__ == "__main__":
    main()
