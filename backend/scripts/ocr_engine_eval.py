"""
OCR engine technical comparison for Phase 3.7.

The brief requires choosing ONE primary OCR engine after a small
comparison, weighted on Arabic quality, Windows reliability, latency,
dependency size.

This script measures what actually happens rather than trusting a
library's advertised capability. The interesting result is that
EasyOCR's Arabic is recognised but emitted in REVERSED logical order,
which is a bidi defect, not a recognition failure -- so it can be
repaired deterministically.
"""
import os
import time
import unicodedata

from PIL import Image, ImageDraw, ImageFont

TEMP = os.environ.get("TEMP", ".")
OUT = os.path.join(TEMP, "ocr_eval")
os.makedirs(OUT, exist_ok=True)

FONT = "C:/Windows/Fonts/tahoma.ttf"

CASES = {
    "english_bait": [
        ("Verify your bank account", 52),
        ("ALERT: your account will be closed", 38),
        ("https://secure-bank-verify.example/login", 32),
    ],
    "arabic_bait": [
        ("الرجاء تأكيد حسابك الآن", 34),
        ("سيتم إغلاق حسابك خلال ٢٤ ساعة", 30),
        ("اضغط هنا لتأكيد هويتك", 30),
    ],
    "mixed": [
        ("تحقق من حسابك", 34),
        ("Account verification", 34),
        ("https://bank-login.example/confirm", 28),
    ],
}


def render(name, lines):
    path = os.path.join(OUT, f"{name}.png")
    img = Image.new("RGB", (1000, 120 + 90 * len(lines)), "white")
    d = ImageDraw.Draw(img)
    y = 40
    for text, size in lines:
        d.text((40, y), text, font=ImageFont.truetype(FONT, size), fill="black")
        y += 90
    img.save(path)
    return path


def norm(s):
    """Strip punctuation/whitespace and Arabic diacritics for scoring."""
    s = unicodedata.normalize("NFKC", s)
    out = []
    for ch in s:
        if ch.isspace():
            continue
        if unicodedata.category(ch).startswith("P"):
            continue
        if 0x064B <= ord(ch) <= 0x0652:  # Arabic diacritics
            continue
        out.append(ch)
    return "".join(out)


def has_arabic(s):
    return any(0x0600 <= ord(c) <= 0x06FF for c in s)


def score(pred, truth):
    """Character recall/precision on the normalised strings."""
    p, t = norm(pred), norm(truth)
    if not t:
        return None
    hits = sum(1 for a, b in zip(p, t) if a == b)
    recall = hits / len(t)
    precision = hits / len(p) if p else 0.0
    return {
        "recall": round(recall, 3),
        "precision": round(precision, 3),
        "exact": p == t,
        "reversed_exact": p == t[::-1],
    }


def main():
    paths = {k: render(k, v) for k, v in CASES.items()}
    report = {}

    import easyocr
    t0 = time.time()
    reader = easyocr.Reader(["en", "ar"], gpu=False, verbose=False)
    load_s = time.time() - t0
    print(f"easyocr loaded in {load_s:.1f}s")

    ar_rows, en_rows = [], []
    for name, path in paths.items():
        t0 = time.time()
        results = reader.readtext(path, detail=1, paragraph=False)
        dt = time.time() - t0
        for _, txt, conf in results:
            row = {"image": name, "raw": txt, "conf": round(conf, 3), "secs": round(dt, 2)}
            ar_rows.append(row) if has_arabic(txt) else en_rows.append(row)

    print("\n--- ENGLISH LINES ---")
    for r in en_rows:
        print(f"  conf={r['conf']:.3f} {r['raw']!r}")

    print("\n--- ARABIC LINES: raw vs order-reversed ---")
    ar_fixed = 0
    for r in ar_rows:
        rev = r["raw"][::-1]
        print(f"  conf={r['conf']:.3f} raw={r['raw']!r}")
        print(f"                 rev={rev!r}")
        # does reversing make it match any ground-truth Arabic line?
        truths = [t for t, _ in CASES["arabic_bait"]] + [t for t, _ in CASES["mixed"]]
        best = None
        for t in truths:
            if norm(rev) == norm(t):
                best = t
        if best:
            ar_fixed += 1
            print(f"                 ^ REVERSAL RECOVERS: {best!r}")
    print(f"\narabic lines recovered by reversing: {ar_fixed}/{len(ar_rows)}")

    truth_map = {}
    for lines in CASES.values():
        for t, _ in lines:
            truth_map[norm(t)] = t

    en_scores = [score(r["raw"], truth_map[k]) for r in en_rows for k in truth_map if k]
    en_hits = [s for s in en_scores if s and s["recall"] > 0.6]
    print(f"\nenglish lines well recognised: {len(en_hits)}/{len(en_rows)}")

    report = {
        "engine": "easyocr",
        "version": "1.7.2",
        "load_secs": round(load_s, 1),
        "english_lines": len(en_rows),
        "english_well_recognised": len(en_hits),
        "arabic_lines": len(ar_rows),
        "arabic_recovered_by_reversal": ar_fixed,
        "note": "Arabic recognised but emitted in reversed logical order (bidi defect).",
    }
    import json
    with open(os.path.join(OUT, "easyocr_eval.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    print("\n" + json.dumps(report, indent=2))


if __name__ == "__main__":
    main()