"""
Blind defence test.

BASIRAH sees only opaque filenames and raw bytes. Ground truth is read
AFTER every prediction has been recorded, so nothing in the analysis
path can be influenced by the labels.

The primary metric is the FALSE AUTHENTIC RATE: the proportion of
synthetic images the system places confidently on the authentic side.
For a defence rehearsal that failure is more damaging than an
abstention, which is why abstention is reported rather than penalised.
"""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BLIND = ROOT / "challenge" / "blind"
IMAGES = BLIND / "images"
LABELS = BLIND / "labels.json"
OUT = ROOT / "results" / "phase37"

AUTHENTIC_SIDE = {"no_strong_synthetic_indicators"}


def analyse() -> list[dict]:
    """Run the live analysis path over every blind image."""
    from app.image.service import analyze_image

    rows: list[dict] = []
    files = sorted(p for p in IMAGES.iterdir() if p.is_file())
    print(f"analysing {len(files)} blind image(s) with no labels visible...\n")
    for i, path in enumerate(files, 1):
        try:
            result = analyze_image(path.read_bytes(), original_name=path.name)
        except Exception as exc:  # noqa: BLE001
            rows.append({"file": path.name, "error": f"{type(exc).__name__}: {exc}"})
            continue
        ens = result.get("ensemble", {})
        if ens.get("available") is False:
            rows.append({"file": path.name, "error": ens.get("reason", "ensemble unavailable")})
            continue
        detectors = {d["modelName"].split()[2] if len(d["modelName"].split()) > 2 else "det"
                     for d in ens.get("detectors", [])}
        a = b = None
        for d in ens.get("detectors", []):
            nm = d["modelName"]
            if "Detector A" in nm:
                a = d["syntheticProbability"]
            elif "Detector B" in nm:
                b = d["syntheticProbability"]
        rows.append({
            "file": path.name,
            "assessment": result.get("finalAssessment") or result.get("assessment"),
            "detector_a": a,
            "detector_b": b,
            "agreement": ens.get("detectorAgreement"),
            "distribution": ens.get("distributionStatus"),
            "evidence_quality": ens.get("evidenceQuality"),
            "abstained": bool(ens.get("abstained")),
            "abstention_reasons": ens.get("abstentionReasons", []),
            "trust": (result.get("trustAssessment") or {}).get("value"),
            "provenance": (result.get("provenance") or {}).get("status"),
            "duration_ms": result.get("durationMs"),
        })
        if i % 10 == 0:
            print(f"  {i}/{len(files)}")
    return rows


def score(rows: list[dict]) -> dict:
    """Ground truth is opened only now, after every prediction exists."""
    labels = json.loads(LABELS.read_text(encoding="utf-8"))
    scored: list[dict] = []
    for r in rows:
        if "error" in r:
            continue
        meta = labels.get(r["file"])
        if not meta:
            continue
        scored.append({**r, **meta})

    def metrics(subset: list[dict]) -> dict:
        synth = [r for r in subset if r["label"] == "synthetic"]
        real = [r for r in subset if r["label"] == "real"]
        # FALSE AUTHENTIC: synthetic presented on the authentic side.
        fa = [r for r in synth if r["assessment"] in AUTHENTIC_SIDE]
        caught = [r for r in synth if r["assessment"] == "likely_synthetic"]
        abst = [r for r in synth if r["abstained"]]
        answered = [r for r in synth if not r["abstained"]]
        return {
            "n": len(subset),
            "n_synthetic": len(synth),
            "n_real": len(real),
            "false_authentic_rate": round(len(fa) / len(synth), 4) if synth else None,
            "false_authentic_count": len(fa),
            "detected_synthetic_rate": round(len(caught) / len(synth), 4) if synth else None,
            "abstention_rate": round(len(abst) / len(subset), 4) if subset else None,
            "coverage": round(len(answered) / len(subset), 4) if subset else None,
        }

    overall = metrics(scored)

    per_family: dict[str, dict] = {}
    fams = sorted({r["family"] for r in scored})
    for fam in fams:
        per_family[fam] = metrics([r for r in scored if r["family"] == fam])

    # Per-detector, to expose which detector carries the error.
    per_detector = {}
    for key in ("detector_a", "detector_b"):
        tp = sum(1 for r in scored if r["label"] == "synthetic" and r[key] is not None and r[key] >= 0.5)
        fn = sum(1 for r in scored if r["label"] == "synthetic" and r[key] is not None and r[key] < 0.5)
        tot = tp + fn
        per_detector[key] = {
            "synthetic_n": tot,
            "false_authentic_rate": round(fn / tot, 4) if tot else None,
            "false_authentic_count": fn,
        }

    disagreements = [r for r in scored
                     if r["detector_a"] is not None and r["detector_b"] is not None
                     and (r["detector_a"] >= 0.5) != (r["detector_b"] >= 0.5)]

    dist = defaultdict(int)
    for r in scored:
        dist[r["distribution"] or "unknown"] += 1

    return {
        "overall": overall,
        "per_family": per_family,
        "per_detector_false_authentic": per_detector,
        "detector_disagreements": len(disagreements),
        "distribution_status_counts": dict(dist),
        "provenance_status_counts": dict(
            defaultdict(int, {k: sum(1 for r in scored if r["provenance"] == k)
                              for k in {r["provenance"] for r in scored}})
        ),
        "mean_duration_ms": round(
            sum(r["duration_ms"] or 0 for r in scored) / len(scored), 1) if scored else None,
    }


if __name__ == "__main__":
    started = time.time()
    rows = analyse()
    report = score(rows)
    report["wall_clock_secs"] = round(time.time() - started, 1)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "blind_defense_test.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    (OUT / "blind_predictions.json").write_text(
        json.dumps(rows, indent=2), encoding="utf-8")
    print("\n" + json.dumps(report, indent=2))
