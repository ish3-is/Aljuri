"""
Phase 2B exploratory data analysis.

Report-ready figures only — focused on what bears on BASIRAH's features
and the corpus defects found in Phase 2B. Deliberately not dozens of
decorative charts.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.datasets import load_processed
from app.ml.feature_schema import model_feature_names
from app.services.feature_extractor import extract_features, to_vector
from app.services.url_analyzer import normalize

csv.field_size_limit(10**9)
ROOT = Path(__file__).resolve().parents[1]
EDA = ROOT / "results" / "phase2b" / "eda"

SAMPLE = 120000


def main() -> int:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    EDA.mkdir(parents=True, exist_ok=True)

    rows = load_processed("phiusil")
    rng = np.random.default_rng(42)
    idx = rng.choice(len(rows), size=min(SAMPLE, len(rows)), replace=False)
    sub = [rows[int(i)] for i in idx]

    print(f"featurizing {len(sub):,} sampled rows...")
    vectors, labels = [], []
    for row in sub:
        try:
            vectors.append(to_vector(extract_features(normalize(row.url))))
            labels.append(row.label)
        except Exception:
            continue
    X = np.asarray(vectors, dtype=np.float32)
    y = np.asarray(labels, dtype=int)
    names = model_feature_names()
    print(f"X={X.shape}  phishing_rate={y.mean():.4f}")

    # --- 1. class balance ---
    fig, ax = plt.subplots(figsize=(6, 4), dpi=140)
    counts = [int((y == 0).sum()), int((y == 1).sum())]
    bars = ax.bar(["Legitimate", "Phishing"], counts, color=["#3DDC97", "#FF5D73"])
    for bar, value in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2, value, f" {value:,}",
                ha="center", va="bottom", fontsize=10)
    ax.set_title("PhiUSIIL class balance (orientation-corrected)")
    ax.set_ylabel("Rows")
    fig.tight_layout()
    fig.savefig(EDA / "class_balance.png")
    plt.close(fig)

    # --- 2. the path artifact (the headline finding) ---
    has_path = np.array([len(v.split("://")[-1]) > len(v.split("://")[-1].split("/")[0])
                         for v in [r.normalized for r in sub]])
    fig, ax = plt.subplots(figsize=(6, 4), dpi=140)
    rates = [has_path[y == c].mean() * 100 for c in (0, 1)]
    bars = ax.bar(["Legitimate", "Phishing"], rates, color=["#3DDC97", "#FF5D73"])
    for bar, value in zip(bars, rates):
        ax.text(bar.get_x() + bar.get_width() / 2, value, f" {value:.1f}%",
                ha="center", va="bottom", fontsize=10)
    ax.set_ylabel("% of rows whose URL carries a path")
    ax.set_title("CORPUS DEFECT: legitimate URLs have no path")
    fig.tight_layout()
    fig.savefig(EDA / "path_artifact.png")
    plt.close(fig)

    # --- 3. key feature distributions by class ---
    focus = ["url_length", "hostname_length", "subdomain_depth",
             "hostname_entropy", "path_entropy", "digit_ratio",
             "suspicious_keyword_count", "subdomain_depth"]
    focus = list(dict.fromkeys(focus))
    focus = [f for f in focus if f in names]
    cols = [names.index(f) for f in focus]
    fig, axes = plt.subplots(2, 4, figsize=(16, 7), dpi=140)
    for ax, name, col in zip(axes.ravel(), focus, cols):
        legit = X[y == 0, col]
        phish = X[y == 1, col]
        upper = np.percentile(np.concatenate([legit, phish]), 99)
        ax.hist(legit, bins=60, range=(0, max(upper, 1e-9)),
                alpha=0.6, label="Legitimate", color="#3DDC97")
        ax.hist(phish, bins=60, range=(0, max(upper, 1e-9)),
                alpha=0.6, label="Phishing", color="#FF5D73")
        ax.set_title(name, fontsize=9)
        ax.legend(fontsize=7, frameon=False)
    fig.suptitle("Feature distributions by class (99th percentile shown)", y=1.0)
    fig.tight_layout()
    fig.savefig(EDA / "feature_distributions.png")
    plt.close(fig)

    # --- 4. correlation heatmap over model inputs ---
    subset = names[: len(names)]
    corr = np.corrcoef(X[:, : len(subset)].T)
    fig, ax = plt.subplots(figsize=(11, 9), dpi=130)
    image = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(subset)))
    ax.set_xticklabels(subset, rotation=90, fontsize=6)
    ax.set_yticks(range(len(subset)))
    ax.set_yticklabels(subset, fontsize=6)
    ax.set_title("Feature correlation matrix (model inputs)")
    fig.colorbar(image, ax=ax, fraction=0.046)
    fig.tight_layout()
    fig.savefig(EDA / "feature_correlation.png")
    plt.close(fig)

    print(f"figures written to {EDA}")
    for path in sorted(EDA.glob("*.png")):
        print(f"  {path.name}  ({path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())