#!/usr/bin/env python3
"""Filter FIRMS VIIRS country CSVs to the map AOI and a date cutoff.
Handles the FIRMS year-file format traps: case-folded headers, '/' vs '-'
dates, and letter confidence (l/n/h) — keeps nominal + high only.

Usage: python3 tools/firms_filter.py <cutoff YYYY-MM-DD> <out.csv> <in.csv...>
"""
import csv
import sys

BBOX = (-60.8, -22.4, -54.2, -14.8)   # W, S, E, N — keep in sync with s2_mosaic.py

def main():
    cutoff, out = sys.argv[1], sys.argv[2]
    n_in = n_out = 0
    with open(out, "w", newline="") as fo:
        wr = csv.writer(fo)
        wr.writerow(["longitude", "latitude", "acq_date"])
        for path in sys.argv[3:]:
            with open(path, newline="") as fh:
                rd = csv.DictReader(fh)
                rd.fieldnames = [f.strip().lower() for f in rd.fieldnames]
                for row in rd:
                    n_in += 1
                    conf = (row.get("confidence") or "").strip().lower()
                    if conf == "l":          # drop low-confidence detections
                        continue
                    lon = float(row["longitude"])
                    lat = float(row["latitude"])
                    if not (BBOX[0] <= lon <= BBOX[2] and BBOX[1] <= lat <= BBOX[3]):
                        continue
                    date = row["acq_date"].strip().replace("/", "-")
                    if date > cutoff:
                        continue
                    wr.writerow([f"{lon:.4f}", f"{lat:.4f}", date])
                    n_out += 1
    print(f"{n_in} rows read -> {n_out} kept (bbox, conf>=nominal, <= {cutoff}) -> {out}")

if __name__ == "__main__":
    main()
