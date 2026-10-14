import base64
import io
import json
import requests

DS = "https://datasets-server.huggingface.co"
P = {"dataset": "OwensLab/CommunityForensics-Small", "config": "default", "split": "train"}

r = requests.get(f"{DS}/rows", params={**P, "offset": 0, "length": 1}, timeout=180)
d = r.json()
print("num_rows_total:", d.get("num_rows_total"), "per_page:", d.get("num_rows_per_page"),
      "partial:", d.get("partial"))

row = d["rows"][0]["row"]
raw = row["image_data"]
print("image_data type:", type(raw).__name__, "len:", len(raw))
try:
    blob = base64.b64decode(raw)
    from PIL import Image
    im = Image.open(io.BytesIO(blob))
    print("DECODED OK ->", im.format, im.size, im.mode, "bytes:", len(blob))
    ex = im.getexif()
    print("EXIF keys:", dict(ex) if ex else "NONE")
except Exception as e:
    print("decode failed:", type(e).__name__, e)
    print(repr(raw)[:200])

# strided offsets -> should hit different model_name values (diverse generators)
print("--- strided offsets 200k apart ---")
for off in [0, 200000, 400000, 700000]:
    rr = requests.get(f"{DS}/rows", params={**P, "offset": off, "length": 1}, timeout=180)
    if rr.status_code == 200:
        x = rr.json()["rows"][0]["row"]
        print(off, "->", x["model_name"], "| arch:", x["architecture"], "| label:", x["label"],
              "| res:", x["resolution"], "| fmt:", x["format"])
    else:
        print(off, "HTTP", rr.status_code, rr.text[:120])