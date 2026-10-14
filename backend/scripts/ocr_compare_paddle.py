"""
PaddleOCR vs EasyOCR on Arabic and English, measured.

Run each engine in a FRESH process. paddlepaddle and torch cannot be
imported into the same interpreter on this host (paddle's DLL search
order breaks torch's shm.dll), which is itself a finding: an engine
that cannot coexist with the detector stack forces a process boundary.
"""

from __future__ import annotations

import json
import os
import sys
import time
import unicodedata

from PIL import Image, ImageDraw, ImageFont

TEMP = os.environ.get("TEMP", ".")
OUT = os.path.join(TEMP, "ocr_eval")
os.makedirs(OUT, exist_ok=True)
FONT = "C:/Windows/Fonts/tahoma.ttf"

TRUTH = {
    "english": [
        "Verify your bank account",
        "ALERT: your account will be closed",
        "Account verification",
    ],
    "arabic": [
        "الرجاء تأكيد حسابك الآن",
        "سيتم إغلاق حسابك خلال ٢٤ ساعة",
        "اضغط هنا لتأكيد هويتك",
    ],
    "urls": [
        "https://secure-bank-verify.example/login",
        "https://bank-login.example/confirm",
    ],
}


def render(name, lines):
    path = os.path.join(OUT, f"{name}.png")
    img = Image.new("RGB", (1000, 130 + 92 * len(lines)), "white")
    d = ImageDraw.Draw(img)
    y = 45
    for text, size in lines:
        d.text((40, y), text, font=ImageFont.truetype(FONT, size), fill="black")
        y += 92
    img.save(path)
    return path


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    out = []
    for ch in s:
        if ch.isspace() or unicodedata.category(ch).startswith("P"):
            continue
        if 0x064B <= ord(ch) <= 0x0652:
            continue
        out.append(ch)
    return "".join(out)


def char_recall(pred: str, truth: str) -> float:
    p, t = norm(pred), norm(truth)
    if not t:
        return 0.0
    return sum(1 for a, b in zip(p, t) if a == b) / len(t)


def run_paddle():
    from paddleocr import PaddleOCR
    t0 = time.time()
    ocr = PaddleOCR(lang="ar", use_doc_orientation_classify=False,
                    use_doc_unwarping=False, use_textline_orientation=False)
    load = time.time() - t0
    results = {}
    for name in ("english", "arabic", "urls"):
        img = render(name, [(t, 46) for t in TRUTH[name]])
        t0 = time.time()
        lines, confs = [], []
        for r in ocr.predict(img):
            rec = r.json["res"] if "res" in getattr(r, "json", {}) else None
            if rec:
                for t, c in zip(rec["rec_texts"], rec["rec_scores"]):
                    lines.append(t)
                    confs.append(float(c))
        results[name] = {"lines": lines, "confs": [round(c, 3) for c in confs],
                         "secs": round(time.time() - t0, 2)}
    return {"engine": "paddleocr", "load_secs": round(load, 1), "results": results}


def score(results):
    """Best-truth match per detected line, in logical order."""
    summary = {}
    for name, truth_lines in TRUTH.items():
        got = results.get(name, {}).get("lines", [])
        joined = " ".join(got)
        joined_rev = joined[::-1]
        exact = sum(1 for t in truth_lines if norm(t) in joined)
        exact_rev = sum(1 for t in truth_lines if norm(t) in joined_rev)
        recalls = []
        for t in truth_lines:
            recalls.append(max(char_recall(joined, t), char_recall(joined_rev, t)))
        summary[name] = {
            "truth_lines": len(truth_lines),
            "exact_as_returned": exact,
            "exact_after_reversal": exact_rev,
            "mean_best_char_recall": round(sum(recalls) / len(recalls), 3),
        }
    return summary


if __name__ == "__main__":
    engine = sys.argv[1]
    if engine == "paddle":
        out = run_paddle()
        out["score"] = score(out["results"])
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        raise SystemExit("usage: ocr_compare.py paddle")
