"""Sequentially download CommunityForensics shards, verify, extract, delete.

Changes vs the earlier parallel version, after three shards came back TRUNCATED:
  * strictly SEQUENTIAL: one shard in flight at a time, so a timeout/kill cannot
    leave several half-written files behind
  * every download is VERIFIED before use: size must equal the server's
    Content-Length AND the first/last 4 bytes must both be b'PAR1'. A truncated
    parquet has PAR1 only at the head, and pyarrow's "magic bytes not found in
    footer" is exactly the failure we are guarding against.
  * a corrupt file is DELETED and reported, never silently read
  * extraction verifies each image decodes before it is counted
"""
import argparse
import base64
import hashlib
import io
import json
import os
import time
from collections import Counter, defaultdict

import fsspec
import pyarrow.parquet as pq
import requests
from PIL import Image

BASE = "https://huggingface.co/datasets/OwensLab/CommunityForensics-Small/resolve/main/data"
IDX = "datasets/image/manifests/_cf_shard_index.json"
OUT_ROOT = "datasets/image/raw/communityforensics_small"
REPO = "OwensLab/CommunityForensics-Small"
STAGE = os.path.join(os.environ.get("LOCALAPPDATA", r"C:\Users\hp\AppData\Local"),
                     "Temp", "basirah_dl")
COLS = ["image_name", "image_data", "model_name", "architecture",
        "label", "format", "resolution", "real_source"]
MAGIC = b"PAR1"


def sanitize(name: str) -> str:
    return "".join(c if (c.isalnum() or c in "-_.") else "_" for c in name)[:70]


def download_verified(url: str, dest: str, tries: int = 3) -> tuple[bool, str]:
    """Download to dest, verifying declared length AND parquet magic at both ends."""
    for attempt in range(1, tries + 1):
        head = requests.head(url, allow_redirects=True, timeout=60)
        expected = int(head.headers.get("Content-Length") or 0)
        got = 0
        t0 = time.time()
        with requests.get(url, stream=True, timeout=300) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(1 << 22):
                    f.write(chunk)
                    got += len(chunk)
                    if got % (300 << 20) < (1 << 22):
                        print(f"    ...{got/1e9:.2f} GB "
                              f"({got/max(time.time()-t0,1):.1f} MB/s)", flush=True)
        size = os.path.getsize(dest)
        with open(dest, "rb") as f:
            head_magic = f.read(4)
            f.seek(-4, os.SEEK_END)
            tail_magic = f.read(4)
        ok_len = (expected == 0) or (size == expected)
        ok_magic = (head_magic == MAGIC and tail_magic == MAGIC)
        if ok_len and ok_magic:
            print(f"    VERIFIED shard: {size/1e9:.2f} GB in {time.time()-t0:.0f}s "
                  f"(expected {expected/1e9:.2f} GB)", flush=True)
            return True, "ok"
        reason = []
        if not ok_len:
            reason.append(f"size {size} != Content-Length {expected}")
        if head_magic != MAGIC:
            reason.append(f"head magic {head_magic!r}")
        if tail_magic != MAGIC:
            reason.append(f"tail magic {tail_magic!r} (TRUNCATED)")
        msg = f"attempt {attempt} failed: {'; '.join(reason)}"
        print("    " + msg, flush=True)
        if os.path.exists(dest):
            os.remove(dest)          # never keep a corrupt shard around
        if attempt == tries:
            return False, msg
    return False, "unreachable"


def plan_rows(meta: dict, per_model_syn: int, real_budget: int) -> list[int]:
    syn_by_model, real_rows = defaultdict(list), []
    for i, (m, a, la) in enumerate(zip(meta["model_name"], meta["architecture"], meta["label"])):
        if la == 1:
            syn_by_model[(a, m)].append(i)
        else:
            real_rows.append(i)
    pick = []
    for key in sorted(syn_by_model):
        rows = syn_by_model[key]
        if per_model_syn > 0:
            pick.extend(rows[:: max(1, len(rows) // per_model_syn)][:per_model_syn])
    if real_budget > 0 and real_rows:
        pick.extend(real_rows[:: max(1, len(real_rows) // real_budget)][:real_budget])
    return sorted(set(pick))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shards", required=True)
    ap.add_argument("--per-model-syn", type=int, default=4)
    ap.add_argument("--real-budget", type=int, default=400)
    ap.add_argument("--out", default="datasets/image/manifests/_cf_records.json")
    args = ap.parse_args()
    shards = [int(s) for s in args.shards.split(",") if s.strip()]
    os.makedirs(STAGE, exist_ok=True)
    idx = json.load(open(IDX))

    out_path = args.out
    prev = json.load(open(out_path)) if os.path.exists(out_path) else []
    by_path = {r["path"]: r for r in prev}
    seen = {r["sha256"] for r in prev}
    status = []

    for sh in shards:
        url = f"{BASE}/HFCF_small_{sh}.parquet"
        local = os.path.join(STAGE, f"cf_{sh}.parquet")
        print(f"=== shard {sh}", flush=True)
        ok, msg = download_verified(url, local)
        if not ok:
            status.append({"shard": sh, "ok": False, "error": msg})
            print(f"=== shard {sh} ABORTED: {msg}", flush=True)
            continue
        n_new = 0
        try:
            want = plan_rows(idx["shards"][str(sh)], args.per_model_syn, args.real_budget)
            d = pq.ParquetFile(local).read(columns=COLS).to_pydict()
            for i in want:
                try:
                    raw = d["image_data"][i]
                    # The datasets-server API serves this column base64-encoded
                    # as a STRING, but in the parquet file itself it is raw
                    # binary. b64decode on raw bytes silently corrupts every
                    # image, so only decode when it is actually str/bytes-of-ascii.
                    if isinstance(raw, str):
                        blob = base64.b64decode(raw)
                    else:
                        blob = bytes(raw)
                    sha = hashlib.sha256(blob).hexdigest()
                    if sha in seen:
                        continue
                    with Image.open(io.BytesIO(blob)) as im:
                        im.verify()          # must decode before we count it
                    with Image.open(io.BytesIO(blob)) as im:
                        w, h = im.size
                    lab = d["label"][i]
                    cls = "synthetic" if lab == 1 else "real"
                    sub = sanitize(d["model_name"][i]) if lab == 1 else "realsrc_NA"
                    os.makedirs(os.path.join(OUT_ROOT, cls), exist_ok=True)
                    fn = f"s{sh}_{i:05d}_{sub}.{'png' if d['format'][i]=='PNG' else 'jpg'}"
                    with open(os.path.join(OUT_ROOT, cls, fn), "wb") as f:
                        f.write(blob)
                    seen.add(sha)
                    by_path[f"{OUT_ROOT}/{cls}/{fn}"] = {
                        "path": f"{OUT_ROOT}/{cls}/{fn}", "label": lab, "class": cls,
                        "generator": d["model_name"][i] if lab == 1 else None,
                        "generator_family": d["architecture"][i] if lab == 1 else None,
                        "generator_documented_by_source": True,
                        "real_source": (d["real_source"][i] if lab == 0 else None) or None,
                        "declared_format": d["format"][i],
                        "declared_resolution": d["resolution"][i],
                        "actual_w": w, "actual_h": h,
                        "bytes": len(blob), "sha256": sha,
                        "shard": sh, "row": i, "hf_repo": REPO,
                        "image_name": d["image_name"][i],
                    }
                    n_new += 1
                except Exception as e:
                    print(f"  row {i}: {type(e).__name__} {e}"[:130], flush=True)
            status.append({"shard": sh, "ok": True, "extracted": n_new})
            print(f"=== shard {sh} extracted {n_new} new", flush=True)
        finally:
            if os.path.exists(local):
                os.remove(local)
            json.dump(list(by_path.values()), open(out_path, "w"))
            recs = list(by_path.values())
            print(f"    running total {len(recs)} "
                  f"(real={sum(1 for r in recs if r['label']==0)}, "
                  f"syn={sum(1 for r in recs if r['label']==1)})", flush=True)

    recs = list(by_path.values())
    json.dump(recs, open(out_path, "w"))
    json.dump(status, open("datasets/image/manifests/_cf_fetch_status.json", "w"), indent=1)
    print("FAMILIES:", dict(Counter(r["generator_family"] for r in recs
                                     if r["label"] == 1).most_common()), flush=True)
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()