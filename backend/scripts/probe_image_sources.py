"""Probe HuggingFace dataset availability (gating) before downloading.

No auth. A 401/403 means gated -> record and skip, never substitute.
"""
import json
import sys
import requests

API = "https://huggingface.co/api/datasets"

CANDIDATES = [
    # synthetic candidates
    "poloclub/diffusiondb",
    "poloclub/diffusiondb-stable-diffusion-xl-1-0",
    "huggan/flowers-102",
    "CIFAKE/imagenet",
    "Bird-bench/AIorNot",
    "elsaEU/ELSA_D3",
    "Ryan-sjtu/mnist-fake",
    "detection-datasets/coco",
    "keremberke/pokemon-classification",
    # real candidates
    "frgfm/imagenette",
    "zh-plus/tiny-imagenet",
    "Maysee/tiny-imagenet",
    "timm/imagenet-1k-wds",
    "HuggingFaceM4/COCO",
    "nlphuji/flickr30k",
    "detection-datasets/fashionpedia",
    "clip-benchmark/wds_vtab-flowers",
    "jxie/coco_captions",
    "sasha/dog-food",
    "ethz/food101",
    "Multimodal-Fatima/OxfordFlowers_train",
    "dpdl-benchmark/oxford_flowers102",
    "beans",
    "cats_vs_dogs",
    "mrm8488/ImageNet1K-val",
    "imagenet-1k",
    "clip-benchmark/wds_imagenetv2",
    "vaishaal/ImageNetV2",
    "songweig/imagenet_sketch",
    "keremberke/animals",
]


def probe(name: str) -> dict:
    url = f"{API}/{name}"
    try:
        r = requests.get(url, timeout=30)
    except Exception as e:  # network-level failure
        return {"name": name, "status": "NETERR", "detail": str(e)[:120]}
    rec = {"name": name, "status": r.status_code}
    if r.status_code == 200:
        d = r.json()
        rec["gated"] = d.get("gated", False)
        rec["private"] = d.get("private", False)
        rec["downloads"] = d.get("downloads")
        rec["tags"] = [t for t in d.get("tags", []) if t.startswith("license:")]
        rec["card_license"] = (d.get("cardData") or {}).get("license")
        rec["n_files_hint"] = len(d.get("siblings") or [])
    else:
        rec["detail"] = r.text[:120]
    return rec


def main() -> None:
    out = []
    for name in CANDIDATES:
        rec = probe(name)
        out.append(rec)
        print(json.dumps(rec), flush=True)
    with open("datasets/image/manifests/_probe_results.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    sys.exit(main())
