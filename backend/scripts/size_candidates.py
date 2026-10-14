"""Measure candidate corpora: total rows, and whether ranged/streamed access is viable."""
import json
import requests

DS = "https://datasets-server.huggingface.co"


def sizes(repo, config=None, split=None):
    r = requests.get(f"{DS}/splits", params={"dataset": repo}, timeout=120)
    out = {}
    if r.status_code != 200:
        return {"http": r.status_code, "body": r.text[:200]}
    for s in r.json().get("splits", []):
        key = f"{s['config']}/{s['split']}"
        out[key] = {"num_rows": s.get("num_rows"), "num_bytes": s.get("num_bytes")}
    return out


for repo in [
    "OwensLab/CommunityForensics-Small",
    "OwensLab/CommunityForensics-Eval",
    "HuggingFaceM4/COCO",
    "nlphuji/flickr30k",
]:
    print("=" * 20, repo)
    print(json.dumps(sizes(repo))[:600], flush=True)

# probe the /rows endpoint: does a large offset work? (strided sampling plan)
for off in [0, 1000, 100000]:
    r = requests.get(
        f"{DS}/rows",
        params={"dataset": "OwensLab/CommunityForensics-Small",
                "config": "default", "split": "train", "offset": off, "length": 2},
        timeout=180,
    )
    print(f"rows offset={off} HTTP {r.status_code}", flush=True)
    if r.status_code == 200:
        d = r.json()
        print("  keys:", list(d.keys()))
        for row in d.get("rows", [])[:2]:
            rr = {k: (f"<{len(v.get('bytes') or '')}b64>" if isinstance(v, dict) and "src" in v else v)
                  for k, v in row["row"].items() if k != "image_data"}
            print("  ", json.dumps(rr)[:400])
        break
    else:
        print("  ", r.text[:200])