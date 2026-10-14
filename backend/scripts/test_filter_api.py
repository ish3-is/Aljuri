"""Test datasets-server /filter so we can pull specific model_name rows cheaply.

Each CF shard is a SINGLE 4 GB row group, so any image read costs ~4 GB.
If /filter works server-side we can select generator models directly.
"""
import json
import requests

DS = "https://datasets-server.huggingface.co"
P = {"dataset": "OwensLab/CommunityForensics-Small", "config": "default", "split": "train"}

# what columns / order does the preview cover?
r = requests.get(f"{DS}/filter",
                 params={**P, "where": "architecture='GAN'", "offset": 0, "length": 3},
                 timeout=180)
print("GAN filter HTTP", r.status_code)
if r.status_code == 200:
    d = r.json()
    print("num_rows_total:", d.get("num_rows_total"))
    for row in d.get("rows", [])[:3]:
        rr = {k: v for k, v in row["row"].items() if k != "image_data"}
        print("  ", json.dumps(rr)[:300])
else:
    print(r.text[:300])

# Is the preview actually the whole dataset when filtering, or only 10k rows?
r2 = requests.get(f"{DS}/filter",
                  params={**P, "where": "label=0", "offset": 0, "length": 1}, timeout=180)
print("label=0 filter HTTP", r2.status_code)
if r2.status_code == 200:
    d2 = r2.json()
    print("num_rows_total for label=0:", d2.get("num_rows_total"))
    if d2.get("rows"):
        x = d2["rows"][0]["row"]
        print("  sample real row:", {k: v for k, v in x.items() if k != "image_data"})

for w in ["architecture='PixDiff'", "architecture='LatDiff'", "architecture='Other'", "label=1"]:
    rr = requests.get(f"{DS}/filter", params={**P, "where": w, "length": 1}, timeout=180)
    if rr.status_code == 200:
        print(f"  {w!r:32} -> total {rr.json().get('num_rows_total')}")
    else:
        print(f"  {w!r:32} -> HTTP {rr.status_code} {rr.text[:80]}")