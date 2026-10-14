"""Full-stack E2E: frontend image provider -> real backend -> mapped result.

Runs the real TypeScript provider logic against the live FastAPI server
using real dataset-labelled images. No mocks on either side.
"""

import io
import json
import subprocess
import sys
import time
from pathlib import Path

import requests

BACKEND = Path(__file__).resolve().parents[1]
PROJECT = BACKEND.parent
BASE = "http://127.0.0.1:8123"

print("starting backend...")
proc = subprocess.Popen(
    [str(BACKEND / ".venv/Scripts/python.exe"), "-m", "uvicorn",
     "app.main:app", "--port", "8123", "--log-level", "warning"],
    cwd=str(BACKEND),
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)
try:
    for _ in range(60):
        try:
            if requests.get(f"{BASE}/api/health", timeout=2).ok:
                break
        except Exception:  # noqa: BLE001
            pass
        time.sleep(1)
    else:
        print("backend did not become ready")
        raise SystemExit(1)

    print("backend ready\n")

    # ---- real dataset-labelled samples ---------------------------
    square = BACKEND / "datasets/image/square"
    real = sorted((square / "real").glob("*.jpg"))[0]
    synthetic = sorted((square / "synthetic").glob("*.jpg"))[0]

    cases = [
        ("corpus-labelled real", real.read_bytes(), "sample.jpg"),
        ("corpus-labelled synthetic", synthetic.read_bytes(), "sample.jpg"),
    ]
    tiny = io.BytesIO()
    from PIL import Image
    Image.new("RGB", (96, 96), (120, 90, 200)).save(tiny, "PNG")
    cases.append(("low-resolution 96x96", tiny.getvalue(), "tiny.png"))
    cases.append(("corrupt png", b"\x89PNG\r\n\x1a\n" + b"junk" * 40, "bad.png"))
    cases.append(("svg", b'<svg xmlns="http://www.w3.org/2000/svg"/>', "x.svg"))
    gif = io.BytesIO()
    Image.new("RGB", (64, 64), (10, 20, 30)).save(gif, "GIF")
    cases.append(("unsupported gif", gif.getvalue(), "x.gif"))

    for label, payload, name in cases:
        response = requests.post(
            f"{BASE}/api/analyze/image",
            files={"file": (name, payload, "application/octet-stream")},
            timeout=90,
        )
        print(f"--- {label} ---")
        print(f"  HTTP {response.status_code}")
        if response.status_code != 200:
            print(f"  code={response.json().get('code')}")
            continue
        body = response.json()
        syn = body["synthetic"]
        p = syn["syntheticProbability"]
        print(f"  assessment     : {body['assessment']}")
        print(f"  P(synthetic)   : {p if p is None else round(p, 4)}")
        print(f"  uncertainty    : [{syn['uncertaintyLower']}, {syn['uncertaintyUpper']}]"
              f"  uncertain={syn['uncertain']}")
        print(f"  trust/conf     : {body['trustScore']} / {body['confidence']}")
        print(f"  model          : {body['model']['modelName']} "
              f"v{body['model']['modelVersion']} [{body['model']['status']}]")
        print(f"  advisory       : {body['safety']['advisoryOnly']}")
        print(f"  metadata       : {body['metadata']['width']}x{body['metadata']['height']} "
              f"{body['metadata']['format']} exif={body['metadata']['exifPresent']}")
        print(f"  provenance     : {body['provenance']['status']}")
        print(f"  forensics      : {len(body['forensics'])} signals")
        print(f"  timeline       : {len(body['timeline'])} stages")
        print(f"  quality flags  : {[w['code'] for w in body['evidenceQuality']['warnings']]}")
        print()

    # ---- URL flow still real --------------------------------------
    print("--- URL flow (regression) ---")
    r = requests.post(f"{BASE}/api/analyze/url",
                      json={"url": "https://github.com/anthropics"}, timeout=60)
    body = r.json()
    print(f"  HTTP {r.status_code}  trust={body.get('trustScore')} risk={body.get('riskLevel')}")
    info = requests.get(f"{BASE}/api/model/info", timeout=30).json()
    print(f"  model={info.get('modelName')} blocking={info.get('fit_for_automated_blocking')}")

finally:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except Exception:  # noqa: BLE001
        proc.kill()
    print("\nbackend stopped")
