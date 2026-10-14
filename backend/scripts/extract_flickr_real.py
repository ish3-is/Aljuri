"""Extract REAL images from flickr30k-images.zip as individual files.

Flickr30k is genuinely useful for the "real" class here: consumer-camera photos
from Flickr, so we get varied cameras, varied resolutions and real JPEG
compression -- exactly the diversity a detector must not be able to shortcut.

Only a bounded sample is extracted (the zip holds ~31k photos); we stride
through the archive so the sample spans the whole filename range rather than
only the alphabetically first N.
"""
import hashlib
import io
import json
import os
import zipfile
from collections import Counter

from PIL import Image

ZIP = os.path.join(os.environ.get("LOCALAPPDATA", r"C:\Users\hp\AppData\Local"),
                   "Temp", "basirah_dl", "flickr30k-images.zip")
OUT = "datasets/image/raw/flickr30k/real"
SRC_URL = "https://huggingface.co/datasets/nlphuji/flickr30k/resolve/main/flickr30k-images.zip"


def main() -> None:
    target = int(os.environ.get("N_REAL", "3000"))
    os.makedirs(OUT, exist_ok=True)
    z = zipfile.ZipFile(ZIP)
    names = [n for n in z.namelist()
             if n.lower().endswith((".jpg", ".jpeg")) and "__MACOSX" not in n]
    names.sort()
    print(f"candidate photos in zip: {len(names)}", flush=True)
    stride = max(1, len(names) // target)
    picked = names[::stride][:target]

    recs, seen = [], set()
    fails = 0
    for n in picked:
        try:
            blob = z.read(n)
            sha = hashlib.sha256(blob).hexdigest()
            if sha in seen:
                continue
            # decode-verify BEFORE writing: a row in a zip is not proof of an image
            with Image.open(io.BytesIO(blob)) as im:
                im.verify()
            with Image.open(io.BytesIO(blob)) as im:
                w, h, fmt, mode = im.size[0], im.size[1], im.format, im.mode
                exif = im.getexif()
            if exif:
                make = exif.get(0x010F)
                model = exif.get(0x0110)
            else:
                make = model = None
            seen.add(sha)
            fn = os.path.basename(n)
            with open(os.path.join(OUT, fn), "wb") as f:
                f.write(blob)          # verbatim, no re-encode
            recs.append({
                "path": f"datasets/image/raw/flickr30k/real/{fn}",
                "label": 0, "class": "real",
                "generator": None, "generator_family": None,
                "generator_documented_by_source": True,
                "real_source": "flickr30k",
                "declared_format": None, "declared_resolution": None,
                "actual_w": w, "actual_h": h, "actual_format": fmt, "mode": mode,
                "bytes": len(blob), "sha256": sha,
                "exif_present": bool(exif),
                "exif_make": make, "exif_model": model,
                "zip_member": n, "hf_repo": "nlphuji/flickr30k",
            })
        except Exception as e:
            fails += 1
            print(f"  skip {n}: {type(e).__name__} {e}"[:120], flush=True)
    json.dump(recs, open("datasets/image/manifests/_flickr_records.json", "w"))
    print(f"EXTRACTED {len(recs)} real images, {fails} failed", flush=True)
    print("formats:", dict(Counter(r["actual_format"] for r in recs)), flush=True)
    print("exif present:", sum(1 for r in recs if r["exif_present"]), "/", len(recs), flush=True)
    print("top makes:", Counter(r["exif_make"] for r in recs
                               if r["exif_make"]).most_common(10), flush=True)


if __name__ == "__main__":
    main()