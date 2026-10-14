"""Write the Phase 2D corpora to datasets/processed/.

The adapters for the realistic legitimate corpus and PhishTank were
registered and used for training, but their cleaned output was never
persisted, so load_processed() fails for them. This writes both files
using the adapters themselves, so the persisted form and the training
path are the same code.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.corpus_adapters import ADAPTERS
from app.ml.datasets import PROCESSED_DIR, write_processed


def main() -> int:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    for name in ("realistic", "phishtank"):
        if name not in ADAPTERS:
            print(f"  {name}: no adapter registered")
            continue
        started = time.perf_counter()
        adapter = ADAPTERS[name]()
        rows = adapter.load()
        path = write_processed(rows, name)
        context = adapter.context()
        print(
            f"  {name:10} rows={len(rows):>8,}  -> {path.name} "
            f"({path.stat().st_size:,} bytes, {time.perf_counter() - started:.0f}s)"
        )
        for key in ("raw_rows", "malformed", "excluded_by_class"):
            if key in context:
                print(f"             {key}: {context[key]}")

    # The phishing class from the realistic corpus is also useful
    # standalone; record what each file contains.
    print()
    print("available processed corpora:", sorted(p.stem.replace("_clean", "") for p in PROCESSED_DIR.glob("*_clean.csv")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())