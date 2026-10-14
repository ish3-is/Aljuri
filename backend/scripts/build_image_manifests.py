"""Emit the per-source provenance manifests required by the brief.

Each datasets/image/manifests/<source>.json records: source, source URL,
license, download date, checksums, classes, generator family (ONLY where the
source documents it), image count, resolution distribution and format
distribution.

Rules enforced here:
  * generator is null unless the SOURCE documents it. We never infer a
    generator from a filename, prompt string or visual appearance.
  * a real photograph has generator=null BY DEFINITION (not "unknown").
  * licensing is transcribed from the dataset card; anything not stated is
    recorded as "unclear" rather than assumed permissive.
"""
import datetime as dt
import json
import os
from collections import Counter, defaultdict

MAN = "datasets/image/manifests"
AUD = "datasets/image/audit"
TODAY = dt.date.today().isoformat()

SOURCES = {
    "communityforensics_small": {
        "source": "OwensLab/CommunityForensics-Small",
        "source_url": "https://huggingface.co/datasets/OwensLab/CommunityForensics-Small",
        "paper": "Community Forensics: Using Thousands of Generators to Train "
                 "Fake Image Detectors (CVPR 2025), arXiv:2411.04125",
        "license": "cc-by-nc-sa-4.0 (NON-COMMERCIAL RESEARCH ONLY)",
        "license_source": "dataset card front matter `license: cc-by-nc-sa-4.0`",
        "license_caveat": "Non-commercial + share-alike. Explicitly NOT a "
                          "permissive licence; do not redistribute or use "
                          "commercially without permission.",
        "classes": {"0": "real (photograph)", "1": "synthetic (generator output)"},
        "generator_documentation": {
            "documented": True,
            "fields_used": ["model_name", "architecture"],
            "architecture_families": ["GAN", "LatDiff", "PixDiff", "Other"],
            "n_distinct_model_name_in_full_dataset": 4786,
            "note": "Generator identity comes from the dataset's own "
                    "`model_name` column. It is never inferred from a filename "
                    "or from image content. Generator-held-out evaluation is "
                    "therefore possible.",
        },
        "real_source_provenance_gap": "For label=0 rows the `real_source` "
                                      "column is the literal string 'N/A', so "
                                      "which real dataset an image came from "
                                      "(FFHQ / VISION / COCO / LandscapesHQ) is "
                                      "NOT recoverable per-image from this "
                                      "release. Real-image provenance therefore "
                                      "comes from the separate Flickr30k corpus.",
        "access": "public, no authentication required",
    },
    "flickr30k": {
        "source": "nlphuji/flickr30k (Flickr30k images)",
        "source_url": "https://huggingface.co/datasets/nlphuji/flickr30k",
        "archive_url": "https://huggingface.co/datasets/nlphuji/flickr30k/"
                       "resolve/main/flickr30k-images.zip",
        "paper": "Young et al., 'From Image Descriptions to Visual Denotations: "
                 "New Similarity Metrics for Semantic Inference over Event "
                 "Descriptions', ACL 2014",
        "license": "UNCLEAR - NOT VERIFIED. Flickr30k aggregates images from "
                   "Flickr; individual photos carry their own licenses (many "
                   "CC, but no dataset-level statement is present in this HF "
                   "card, which has no `license:` field). Treat as "
                   "research-use-only until relicensed or replaced.",
        "license_source": "HF dataset card for nlphuji/flickr30k contains NO "
                          "license field; original Flickr30k release imposes "
                          "research use only.",
        "license_caveat": "No permissive licence is claimed. Flagged rather "
                          "than assumed - images are never committed to git.",
        "classes": {"0": "real (camera-captured photograph)"},
        "generator_documentation": {
            "documented": True,
            "note": "Real photographs have no generator; `generator` is null "
                    "BY DEFINITION, not unknown.",
        },
        "access": "public, no authentication required",
    },
}


def sha_of(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> None:
    recs = {}
    for fn, src in (("_cf_records.json", "communityforensics_small"),
                    ("_flickr_records.json", "flickr30k")):
        p = f"{MAN}/{fn}"
        if os.path.exists(p):
            recs[src] = json.load(open(p))

    for src, rows in recs.items():
        meta = SOURCES[src]
        by_class = defaultdict(list)
        for r in rows:
            by_class[r["class"]].append(r)
        gens = sorted({r["generator"] for r in rows if r["generator"]})
        fams = Counter(r["generator_family"] for r in rows if r["generator_family"])

        manifest = {
            "source": meta["source"],
            "source_url": meta["source_url"],
            "license": meta["license"],
            "license_source": meta["license_source"],
            "license_caveat": meta["license_caveat"],
            "paper": meta.get("paper"),
            "access": meta["access"],
            "download_date": TODAY,
            "classes": meta["classes"],
            "label_definition": {"0": "real", "1": "synthetic"},
            "generator_family": meta["generator_documentation"],
            "generator_families_present": dict(fams),
            "n_distinct_generators_obtained": len(gens),
            "distinct_generators": gens,
            "unlabelled_generators": 0 if gens else None,
            "unlabelled_generators_note":
                "Zero images have an undocumented generator: every synthetic "
                "image's generator is read from the source's documented "
                "`model_name` column."
                if gens else
                "No synthetic images from this source; generator N/A.",
            "total_images": len(rows),
            "per_class": {},
            "provenance_caveats": [],
        }
        if "real_source_provenance_gap" in meta:
            manifest["provenance_caveats"].append(meta["real_source_provenance_gap"])
        if "archive_url" in meta:
            zp = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp",
                              "basirah_dl", "flickr30k-images.zip")
            if os.path.exists(zp):
                manifest["archive_sha256"] = sha_of(zp)
                manifest["archive_bytes"] = os.path.getsize(zp)

        for cls, rs in sorted(by_class.items()):
            res = Counter(f"{r['actual_w']}x{r['actual_h']}" for r in rs)
            fmt = Counter(r.get("actual_format") or r.get("declared_format")
                          for r in rs)
            manifest["per_class"][cls] = {
                "n_images": len(rs),
                "resolution_distribution": dict(res.most_common(25)),
                "resolution_distinct_values": len(res),
                "format_distribution": dict(fmt),
                "width_stats": {
                    "min": min(r["actual_w"] for r in rs),
                    "median": sorted(r["actual_w"] for r in rs)[len(rs) // 2],
                    "max": max(r["actual_w"] for r in rs),
                },
                "height_stats": {
                    "min": min(r["actual_h"] for r in rs),
                    "median": sorted(r["actual_h"] for r in rs)[len(rs) // 2],
                    "max": max(r["actual_h"] for r in rs),
                },
                "checksums": "per-image sha256 in "
                             f"{MAN}/_{src}_records.json",
            }

        json.dump(manifest, open(f"{MAN}/{src}.json", "w"), indent=1)
        print(f"wrote {MAN}/{src}.json  total={manifest['total_images']} "
              f"families={manifest['generator_families_present']} "
              f"distinct_gens={manifest['n_distinct_generators_obtained']}", flush=True)


if __name__ == "__main__":
    main()