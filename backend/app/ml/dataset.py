"""
Dataset loading, cleaning and label normalisation.

Supports CSV input for a real labelled dataset. Accepts the label
vocabularies commonly used in phishing research so an existing dataset
does not have to be rewritten first.

LABEL NORMALISATION
-------------------
    1, "1", "true",  "yes", "phishing", "malicious", "bad",  "fraud"  -> 1
    0, "0", "false", "no",  "legit",    "benign",     "good", "safe"   -> 0

Anything else raises. An unrecognised label is never silently coerced to
0, because that would quietly poison the training set.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

PHISHING_LABELS = {
    "1", "true", "yes", "y", "phishing", "phish", "malicious",
    "bad", "fraud", "spam", "1.0",
}
BENIGN_LABELS = {
    "0", "false", "no", "n", "legit", "legitimate", "benign",
    "good", "safe", "normal", "0.0",
}

REQUIRED_COLUMNS = ("url",)


@dataclass(frozen=True)
class DatasetRow:
    url: str
    label: int  # 1 = phishing, 0 = benign


@dataclass
class DatasetReport:
    """Provenance of a loaded dataset, for the model metadata file."""

    path: str
    total_rows: int
    phishing_rows: int
    benign_rows: int
    skipped_invalid: int
    skipped_duplicate: int
    columns_found: list[str]

    @property
    def is_balanced(self) -> bool:
        return self.phishing_rows == self.benign_rows

    def as_dict(self) -> dict[str, object]:
        return {
            "path": Path(self.path).name,
            "total_rows": self.total_rows,
            "phishing_rows": self.phishing_rows,
            "benign_rows": self.benign_rows,
            "skipped_invalid": self.skipped_invalid,
            "skipped_duplicate": self.skipped_duplicate,
            "columns_found": self.columns_found,
            "is_balanced": self.is_balanced,
        }


class DatasetError(ValueError):
    """Raised when a dataset cannot be used for training."""


def normalize_label(raw: str) -> int:
    """Map any supported label vocabulary onto 0 or 1."""
    value = str(raw).strip().lower()
    if value in PHISHING_LABELS:
        return 1
    if value in BENIGN_LABELS:
        return 0
    raise DatasetError(
        f"Unrecognised label {raw!r}. Use 0/1, phishing/legitimate, or "
        f"benign/malicious."
    )


def _find_columns(fieldnames: list[str]) -> tuple[str, str]:
    """Locate the url and label columns, tolerating naming variation."""
    lowered = {name.strip().lower(): name for name in fieldnames if name}

    url_column = next(
        (lowered[c] for c in ("url", "urls", "uri", "link") if c in lowered), None
    )
    label_column = next(
        (
            lowered[c]
            for c in ("label", "labels", "class", "target", "y", "is_phishing")
            if c in lowered
        ),
        None,
    )

    if url_column is None:
        raise DatasetError(
            f"No URL column found. Expected one of url/urls/uri/link. "
            f"Columns present: {fieldnames}"
        )
    if label_column is None:
        raise DatasetError(
            f"No label column found. Expected one of "
            f"label/class/target/y/is_phishing. Columns present: {fieldnames}"
        )
    return url_column, label_column


def load_csv(path: str | Path) -> tuple[list[DatasetRow], DatasetReport]:
    """Load a labelled CSV into rows plus a provenance report."""
    path = Path(path)
    if not path.exists():
        raise DatasetError(f"Dataset not found: {path}")

    rows: list[DatasetRow] = []
    seen: set[str] = set()
    skipped_invalid = 0
    skipped_duplicate = 0
    phishing = 0
    benign = 0
    columns: list[str] = []

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise DatasetError(f"Dataset is empty or has no header: {path}")

        columns = list(reader.fieldnames)
        url_column, label_column = _find_columns(columns)

        for record in reader:
            raw_url = (record.get(url_column) or "").strip()
            raw_label = (record.get(label_column) or "").strip()

            if not raw_url or not raw_label:
                skipped_invalid += 1
                continue

            try:
                label = normalize_label(raw_label)
            except DatasetError:
                # An unrecognised label means the file does not match the
                # documented format. Fail loudly rather than guess.
                raise

            key = raw_url.lower()
            if key in seen:
                skipped_duplicate += 1
                continue
            seen.add(key)

            rows.append(DatasetRow(url=raw_url, label=label))
            if label == 1:
                phishing += 1
            else:
                benign += 1

    if not rows:
        raise DatasetError(f"No usable rows in {path}")

    report = DatasetReport(
        path=str(path),
        total_rows=len(rows),
        phishing_rows=phishing,
        benign_rows=benign,
        skipped_invalid=skipped_invalid,
        skipped_duplicate=skipped_duplicate,
        columns_found=columns,
    )
    return rows, report


def write_csv(path: str | Path, rows: list[DatasetRow]) -> None:
    """Write rows back out in the documented format."""
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["url", "label"])
        for row in rows:
            writer.writerow([row.url, row.label])
