"""
Arabic OCR evaluation on genuine browser-rendered screenshots.

Run one engine per process: paddle/torch DLL conflicts aside, keeping
each run isolated also means a crash in one engine cannot silently
contaminate the other's numbers.

Usage:  python ocr_eval_real.py easyocr|tesseract
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path

FIXTURES = Path(os.environ.get("TEMP", ".")) / "basirah_qa" / "ocr_real"
TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSDATA = Path(__file__).resolve().parents[1] / "tools" / "tessdata"

URL_RE = re.compile(r"https?://[^\s<>\"']+")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    # Arabic presentation forms -> base letters, drop tatweel/diacritics
    s = s.replace("\u0640", "")
    out = []
    for ch in s:
        if ch.isspace() or unicodedata.category(ch).startswith("P"):
            continue
        if 0x064B <= ord(ch) <= 0x0652 or 0x0670 <= ord(ch) <= 0x0670:
            continue
        out.append(ch)
    return "".join(out)


def char_recall(pred: str, truth: str) -> float:
    """
    Best character-level recall of `truth` anywhere in `pred`.

    Comparing the whole OCR output against one short phrase is wrong:
    the output legitimately contains many other lines, so a zipped
    positional comparison reports failure even when the phrase is
    present and perfect. Containment is the correct test, and a local
    window is allowed so a trailing bidi mark or spacing variant does
    not invalidate an otherwise exact match.
    """
    p, t = norm(pred), norm(truth)
    if not t:
        return None
    if t in p:
        return 1.0
    width = len(t)
    best = 0.0
    for start in range(0, max(len(p) - width + 1, 1)):
        window = p[start:start + width + 2]
        hits = sum(1 for i, ch in enumerate(t) if i < len(window) and window[i] == ch)
        best = max(best, hits / len(t))
    return best


def load_truth():
    data = json.loads((FIXTURES / "ground_truth.json").read_text(encoding="utf-8"))
    return {d["name"]: d["expect"] for d in data}


def run_easyocr():
    import easyocr
    reader = easyocr.Reader(["ar", "en"], gpu=False, verbose=False)
    out = {}
    for name in load_truth():
        t0 = time.time()
        res = reader.readtext(str(FIXTURES / f"{name}.png"), detail=1, paragraph=False)
        out[name] = {
            "lines": [(t, round(float(c), 3)) for _, t, c in res],
            "secs": round(time.time() - t0, 2),
        }
    return out


def run_tesseract():
    import subprocess
    out = {}
    for name in load_truth():
        t0 = time.time()
        proc = subprocess.run(
            [TESSERACT, str(FIXTURES / f"{name}.png"), "stdout",
             "-l", "ara+eng", "--tessdata-dir", str(TESSDATA), "--psm", "6"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        lines = [l.strip() for l in proc.stdout.splitlines() if l.strip()]
        out[name] = {"lines": [(l, None) for l in lines],
                     "secs": round(time.time() - t0, 2)}
    return out


def score(engine_name: str, raw: dict):
    truth = load_truth()
    report = {"engine": engine_name, "per_fixture": {}}
    ar_hits = ar_total = 0
    en_hits = en_total = 0
    url_hits = url_total = 0

    for name, exp in truth.items():
        lines = raw.get(name, {}).get("lines", [])
        joined = " ".join(t for t, _ in lines)
        joined_rev = joined[::-1]

        ar_checks = []
        for t in exp["ar"]:
            ar_total += 1
            best = max(char_recall(joined, t) or 0, char_recall(joined_rev, t) or 0)
            ar_checks.append(round(best, 3))
            if best >= 0.85:
                ar_hits += 1
        en_checks = []
        for t in exp["en"]:
            en_total += 1
            best = max(char_recall(joined, t) or 0, char_recall(joined_rev, t) or 0)
            en_checks.append(round(best, 3))
            if best >= 0.85:
                en_hits += 1
        found_urls = URL_RE.findall(joined)
        url_checks = []
        for u in exp["urls"]:
            url_total += 1
            exact = any(u.rstrip(".,") in got.rstrip(".,") for got in found_urls)
            url_checks.append({"url": u, "exact": exact})
            if exact:
                url_hits += 1

        report["per_fixture"][name] = {
            "secs": raw.get(name, {}).get("secs"),
            "detected_lines": len(lines),
            "raw_lines": [t for t, _ in lines],
            "arabic_expected": exp["ar"],
            "arabic_char_recall": ar_checks,
            "english_expected": exp["en"],
            "english_char_recall": en_checks,
            "urls_expected": exp["urls"],
            "urls_found": found_urls,
            "url_results": url_checks,
        }

    report["summary"] = {
        "arabic_lines_pass": f"{ar_hits}/{ar_total}",
        "arabic_pass_rate": round(ar_hits / ar_total, 3) if ar_total else None,
        "english_lines_pass": f"{en_hits}/{en_total}",
        "english_pass_rate": round(en_hits / en_total, 3) if en_total else None,
        "urls_exact": f"{url_hits}/{url_total}",
        "url_pass_rate": round(url_hits / url_total, 3) if url_total else None,
    }
    return report


if __name__ == "__main__":
    which = sys.argv[1]
    raw = run_easyocr() if which == "easyocr" else run_tesseract()
    rep = score(which, raw)
    out_path = FIXTURES / f"result_{which}.json"
    out_path.write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(rep, indent=2, ensure_ascii=False))
