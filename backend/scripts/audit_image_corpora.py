"""Audit acquired image corpora and hunt for shortcuts.

For every corpus: count, width/height distribution, format distribution,
file-size distribution, JPEG-quality estimate, EXIF presence and camera makes.
Then compare real vs synthetic SIDE BY SIDE -- the point of the exercise,
because a detector at 0.99 accuracy is worthless if a corpus-classifier can
reach the same score using only container/size/EXIF.

Each corpus is audited from the record manifests written at extraction time,
and every image is opened to confirm it decodes before being counted.
"""
import io
import json
import os
from collections import Counter, defaultdict

from PIL import Image

ROOT = "datasets/image"
MAN = f"{ROOT}/manifests"
AUD = f"{ROOT}/audit"


def jpeg_quality_estimate(path: str, size: int) -> int | None:
    """Estimate JPEG quality by matching file size against re-encodes.

    The original quantisation tables are not recoverable from an already-JPEGed
    image without a reference, so this is a size-ratio ESTIMATE only.
    """
    try:
        with Image.open(path) as im:
            if im.format != "JPEG":
                return None
            im.load()
            rgb = im.convert("RGB")
        best, bestd = None, None
        for q in (95, 90, 85, 80, 75, 70, 60, 50, 40, 30, 20):
            b = io.BytesIO()
            rgb.save(b, "JPEG", quality=q)
            d = abs(len(b.getvalue()) - size)
            if bestd is None or d < bestd:
                best, bestd = q, d
        return best
    except Exception:
        return None


def stats(v):
    if not v:
        return {}
    v = sorted(v)
    n = len(v)
    return {"min": v[0], "p25": v[n // 4], "median": v[n // 2],
            "p75": v[3 * n // 4], "max": v[-1], "mean": round(sum(v) / n, 1)}


def audit_corpus(name, source, cls, family, recs):
    widths, heights, px, sizes = [], [], [], []
    fmt_c, mode_c, exif_c, makes, models = Counter(), Counter(), 0, Counter(), Counter()
    qualities, broken, res_hist = [], [], Counter()
    for r in recs:
        p = r["path"]
        if not os.path.exists(p):
            broken.append({"path": p, "error": "missing on disk"})
            continue
        try:
            size = os.path.getsize(p)
            with Image.open(p) as im:
                im.verify()                      # must decode to be counted
            with Image.open(p) as im:
                w, h = im.size
                fmt_c[im.format] += 1
                mode_c[im.mode] += 1
                ex = im.getexif()
                if ex:
                    exif_c += 1
                    if ex.get(0x010F):
                        makes[str(ex.get(0x010F)).strip()] += 1
                    if ex.get(0x0110):
                        models[str(ex.get(0x0110)).strip()] += 1
            widths.append(w); heights.append(h); px.append(w * h); sizes.append(size)
            res_hist[f"{w}x{h}"] += 1
            if fmt_c.most_common(1)[0][0] == "JPEG" and len(qualities) < 400:
                q = jpeg_quality_estimate(p, size)
                if q:
                    qualities.append(q)
        except Exception as e:
            broken.append({"path": p, "error": f"{type(e).__name__}: {e}"[:90]})
    qs = qualities
    return {
        "corpus": name, "source": source, "class": cls,
        "generator_family": family,
        "label": 0 if cls == "real" else 1,
        "n_images_declared": len(recs),
        "n_images_verified_decoding": len(sizes),
        "n_undecodable_or_missing": len(broken),
        "undecodable_examples": broken[:5],
        "width": stats(widths), "height": stats(heights), "pixels": stats(px),
        "orientation": {
            "landscape": sum(1 for w, h in zip(widths, heights) if w > h),
            "portrait": sum(1 for w, h in zip(widths, heights) if h > w),
            "square": sum(1 for w, h in zip(widths, heights) if w == h),
        },
        "format": dict(fmt_c), "mode": dict(mode_c),
        "file_bytes": stats(sizes),
        "megapixels_hist": dict(Counter(
            ("<0.1MP" if p < 1e5 else "0.1-0.5MP" if p < 5e5 else
             "0.5-1MP" if p < 1e6 else "1-2MP" if p < 2e6 else ">=2MP")
            for p in px)),
        "top_resolutions": dict(res_hist.most_common(12)),
        "resolution_hist": dict(res_hist),
        "exif_present": exif_c,
        "exif_present_pct": round(100 * exif_c / max(1, len(sizes)), 1),
        "camera_makes": dict(makes.most_common(15)),
        "camera_models": dict(models.most_common(15)),
        "jpeg_quality_estimate_mean": round(sum(qs) / len(qs), 1) if qs else None,
        "jpeg_quality_estimate_distribution": dict(Counter(qs)) if qs else None,
        "jpeg_quality_estimate_note": (
            "size-ratio estimate on a <=400-image subsample; not the true "
            "quantisation table"),
    }


def shortcut_report(audits: dict) -> dict:
    real = [a for a in audits.values()
            if a["class"] == "real" and a["n_images_verified_decoding"]]
    syn = [a for a in audits.values()
           if a["class"] == "synthetic" and a["n_images_verified_decoding"]]

    def merge(group):
        f, mp, ex, n, res, qual = Counter(), Counter(), [], 0, Counter(), []
        for g in group:
            n += g["n_images_verified_decoding"]
            f.update(g["format"])
            mp.update(g["megapixels_hist"])
            ex.append(g["exif_present_pct"])
            res.update(g["resolution_hist"])
            if g.get("jpeg_quality_estimate_mean") is not None:
                qual.append(g["jpeg_quality_estimate_mean"])
        return {"corpora": [g["corpus"] for g in group], "n_images": n,
                "format_pct": {k: round(100 * v / max(1, n), 1) for k, v in f.most_common()},
                "megapixels_pct": {k: round(100 * v / max(1, n), 1) for k, v in mp.most_common()},
                "exif_present_pct_mean": round(sum(ex) / len(ex), 1) if ex else None,
                "top_resolutions": dict(res.most_common(10)),
                "jpeg_quality_estimate_mean": round(sum(qual) / len(qual), 1) if qual else None}

    side = {"real": merge(real) if real else {}, "synthetic": merge(syn) if syn else {}}
    risks = {}
    if real and syn:
        ev = []
        rf, sf = side["real"]["format_pct"], side["synthetic"]["format_pct"]
        for k in set(rf) | set(sf):
            a, b = rf.get(k, 0.0), sf.get(k, 0.0)
            if abs(a - b) >= 50:
                ev.append(f"{k}: real {a}% vs synthetic {b}%")
        risks["container_format"] = {
            "risk": bool(ev), "evidence": ev,
            "why": "'is this PNG or JPEG?' classifies without looking at content"}
        ev = []
        rm, sm = side["real"]["megapixels_pct"], side["synthetic"]["megapixels_pct"]
        for k in set(rm) | set(sm):
            a, b = rm.get(k, 0.0), sm.get(k, 0.0)
            if abs(a - b) >= 40:
                ev.append(f"{k}: real {a}% vs synthetic {b}%")
        risks["resolution"] = {
            "risk": bool(ev), "evidence": ev,
            "why": "megapixel count alone is a usable proxy for the label"}
        # IMPORTANT: this bucket-level test is deliberately coarse and CAN
        # report risk=false while an exact-match test reports risk=true. The
        # coarse buckets genuinely overlap (real 88.0% and synthetic 99.3% both
        # land in 0.1-0.5MP), but the precise w x h values are nearly disjoint
        # (real 500x333/500x375 vs synthetic 512x512), which the
        # metadata-only classifier scores at AUC 1.0000. Do not read
        # risk=false here as evidence that geometry is safe.
        risks["resolution"]["coarse_bucket_only"] = True
        risks["resolution"]["exact_wh_measured_by_classifier"] = {
            "auc": 1.0,
            "note": "See datasets/image/audit/corpus_classifier.json; exact "
                    "width/height is a total giveaway despite overlapping "
                    "megapixel buckets."}
        a = side["real"]["exif_present_pct_mean"]
        b = side["synthetic"]["exif_present_pct_mean"]
        ev = ([f"EXIF present: real {a}% vs synthetic {b}%"]
              if a is not None and b is not None and abs(a - b) >= 40 else [])
        risks["exif"] = {
            "risk": bool(ev), "evidence": ev,
            "why": "EXIF presence tracks camera provenance, not authenticity"}
    return {"side_by_side": side, "risks": risks}


def main() -> None:
    os.makedirs(AUD, exist_ok=True)
    groups = defaultdict(list)
    for fn, source in (("_cf_records.json", "communityforensics_small"),
                       ("_flickr_records.json", "flickr30k")):
        p = f"{MAN}/{fn}"
        if not os.path.exists(p):
            print(f"(no {fn})", flush=True)
            continue
        for r in json.load(open(p)):
            groups[(source, r["class"], r.get("generator_family"))].append(r)

    audits = {}
    for (source, cls, fam), recs in sorted(groups.items()):
        if not recs:
            continue
        name = f"{source}_{cls}" + (f"_{fam}" if fam else "")
        a = audit_corpus(name, source, cls, fam, recs)
        audits[name] = a
        json.dump(a, open(f"{AUD}/{name}.json", "w"), indent=1)
        print(f"{name}: declared={a['n_images_declared']} "
              f"verified={a['n_images_verified_decoding']} "
              f"broken={a['n_undecodable_or_missing']} "
              f"fmt={a['format']} exif={a['exif_present_pct']}%", flush=True)

    rep = shortcut_report(audits)
    json.dump({"audits": audits, "shortcuts": rep},
              open(f"{MAN}/_audit_all.json", "w"), indent=1)
    json.dump(rep, open(f"{AUD}/shortcut_report.json", "w"), indent=1)
    print("\n=== SIDE BY SIDE ===")
    print(json.dumps(rep["side_by_side"], indent=1))
    print("\n=== SHORTCUT RISKS ===")
    print(json.dumps(rep["risks"], indent=1))


if __name__ == "__main__":
    main()