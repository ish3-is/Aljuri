"""Full metadata survey of all 186 CommunityForensics-Small shards, CORRECTLY aggregated.

Reads only the small metadata columns (byte-range reads, ~2 s/shard), so the
whole 744 GB dataset is characterised for ~2 MB of transfer.

NOTE: an earlier version aggregated per-shard Counters with a dict
comprehension, which silently OVERWROTE duplicate keys -- the printed
architecture/format/label totals were really just the last shard's numbers.
This version accumulates Counter objects, and also saves a per-shard row index
so later stratified sampling need not re-read the metadata.
"""
import concurrent.futures as cf
import json
from collections import Counter

import fsspec
import pyarrow.parquet as pq

BASE = "https://huggingface.co/datasets/OwensLab/CommunityForensics-Small/resolve/main/data"
META_COLS = ["model_name", "architecture", "label", "subset", "split",
             "format", "resolution", "real_source", "nsfw_flag"]
N_SHARDS = 186

fs = fsspec.filesystem("http", client_kwargs={"trust_env": True})


def shard_meta(n: int) -> dict:
    try:
        with fs.open(f"{BASE}/HFCF_small_{n}.parquet", "rb", block_size=1 << 20) as f:
            pf = pq.ParquetFile(f)
            t = pf.read(columns=META_COLS)
        d = t.to_pydict()
        return {
            "shard": n, "ok": True, "n_rows": t.num_rows,
            "model_name": d["model_name"], "architecture": d["architecture"],
            "label": d["label"], "subset": d["subset"], "split": d["split"],
            "format": d["format"], "resolution": d["resolution"],
            "real_source": d["real_source"], "nsfw_flag": d["nsfw_flag"],
        }
    except Exception as e:
        return {"shard": n, "ok": False, "error": f"{type(e).__name__}: {e}"[:150]}


def main() -> None:
    with cf.ThreadPoolExecutor(max_workers=10) as ex:
        shards = list(ex.map(shard_meta, range(N_SHARDS)))
    ok = [s for s in shards if s["ok"]]
    bad = [s for s in shards if not s["ok"]]
    print(f"shards OK {len(ok)}/{N_SHARDS}, rows {sum(s['n_rows'] for s in ok)}")
    for s in bad:
        print("  FAILED shard", s["shard"], s["error"])

    def tally(col):
        c = Counter()
        for s in ok:
            c.update(s[col])
        return c

    print("\narchitecture:", dict(tally("architecture").most_common()))
    print("label:", dict(tally("label").most_common()))
    print("subset:", dict(tally("subset").most_common()))
    print("distinct model_name:", len(set(tally("model_name"))))

    print("\nformat x label  <-- shortcut check:")
    fxl = Counter()
    for s in ok:
        fxl.update(zip(s["label"], s["format"]))
    for k, v in sorted(fxl.items()):
        print(f"   label={k[0]} format={k[1]}: {v}")

    print("\nresolution x label  <-- shortcut check:")
    rxl = Counter()
    for s in ok:
        rxl.update((la, tuple(r)) for r, la in zip(s["resolution"], s["label"]))
    for k, v in sorted(rxl.items(), key=lambda kv: -kv[1])[:30]:
        print(f"   label={k[0]} res={k[1][0]}x{k[1][1]}: {v}")

    arch_models = {}
    for s in ok:
        for m, a in zip(s["model_name"], s["architecture"]):
            arch_models.setdefault(a, set()).add(m)
    print("\narchitecture -> distinct model_name:")
    for a, ms in sorted(arch_models.items()):
        print(f"   {a}: {len(ms)}")

    idx = {str(s["shard"]): {k: s[k] for k in
                             ("model_name", "architecture", "label", "format",
                              "resolution", "real_source", "subset")}
           for s in ok}
    json.dump({"n_shards": N_SHARDS, "rows": sum(s["n_rows"] for s in ok),
               "architecture": dict(tally("architecture")), "label": dict(tally("label")),
               "format_x_label": {f"{k[0]}|{k[1]}": v for k, v in fxl.items()},
               "resolution_x_label": {f"{k[0]}|{k[1][0]}x{k[1][1]}": v for k, v in rxl.items()},
               "n_models_per_arch": {a: len(m) for a, m in arch_models.items()},
               "shards": idx},
              open("datasets/image/manifests/_cf_shard_index.json", "w"))
    print("\nwrote datasets/image/manifests/_cf_shard_index.json")


if __name__ == "__main__":
    main()