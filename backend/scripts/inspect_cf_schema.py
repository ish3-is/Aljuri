import json
import requests

print("--- modules ---")
for m in ["pyarrow", "fsspec", "huggingface_hub", "datasets"]:
    try:
        mod = __import__(m)
        print(m, getattr(mod, "__version__", "?"))
    except Exception:
        print(m, "MISSING")

r = requests.get(
    "https://datasets-server.huggingface.co/first-rows",
    params={"dataset": "OwensLab/CommunityForensics-Small", "config": "default", "split": "train"},
    timeout=180,
)
print("HTTP", r.status_code)
d = r.json()
if r.status_code != 200:
    print(r.text[:600])
    raise SystemExit
print("FEATURES:", json.dumps(d.get("features"), indent=1)[:1500])
print("NROWS", len(d.get("rows", [])))
for row in d["rows"][:4]:
    rr = dict(row["row"])
    for k, v in list(rr.items()):
        if isinstance(v, dict) and "src" in v:
            rr[k] = "<image bytes=%d>" % len(v.get("bytes") or "")
        elif isinstance(v, str) and len(v) > 160:
            rr[k] = v[:160] + "..."
    print(json.dumps(rr)[:1000])