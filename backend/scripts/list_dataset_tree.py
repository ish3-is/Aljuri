"""List actual files in candidate HF datasets via the tree API (no auth)."""
import json
import sys
import requests

TREE = "https://huggingface.co/api/datasets/{}/tree/main?recursive=1"


def tree(repo: str) -> list[dict]:
    out, cursor = [], None
    for _ in range(6):
        url = f"https://huggingface.co/api/datasets/{repo}/tree/main"
        params = {"recursive": "1"}
        if cursor:
            params["cursor"] = cursor
        r = requests.get(url, params=params, timeout=60)
        if r.status_code != 200:
            return [{"error": f"{r.status_code}: {r.text[:200]}"}]
        batch = r.json()
        if not isinstance(batch, list):
            return [{"error": r.text[:200]}]
        out.extend(batch)
        cursor = batch[-1].get("path") if batch else None
        link = r.headers.get("Link", "")
        if 'rel="next"' not in link:
            break
    return out


for repo in sys.argv[1:]:
    items = tree(repo)
    print(f"===== {repo} : {len(items)} entries")
    if items and "error" in items[0]:
        print("  ERROR", items[0]["error"])
        continue
    # summarise by top-level dir and extension, and show the biggest files
    from collections import Counter
    ext = Counter()
    by_dir = Counter()
    sizes = []
    for it in items:
        if it.get("type") != "file":
            continue
        p = it["path"]
        by_dir[p.split("/")[0] if "/" in p else "<root>"] += 1
        e = p.rsplit(".", 1)[-1].lower() if "." in p else "<noext>"
        ext[e] += 1
        sizes.append((it.get("size") or 0, p))
    print("  ext:", dict(ext.most_common(12)))
    print("  topdirs:", dict(by_dir.most_common(15)))
    sizes.sort(reverse=True)
    print("  biggest:")
    for s, p in sizes[:12]:
        print(f"    {s/1e6:9.2f}MB {p}")
    print("  sample files:", [p for _, p in sizes[:3]], "...", [p for _, p in sizes[-3:]])
    json.dump(items, open(f"datasets/image/manifests/_tree_{repo.replace('/', '__')}.json", "w"))