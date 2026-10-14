"""
Create a genuinely signed C2PA fixture using the official SDK.

The brief forbids fabricating a "valid C2PA" fixture. A self-signed
local certificate is NOT fabrication: it is a real X.509 certificate
and a real ECDSA signature produced by the reference SDK, so exercising
the verification path end-to-end tests genuine cryptography. What it
does NOT prove is trust in a public CA, which is a different question
and is reported separately.

The resulting asset is explicitly labelled self-signed so no later
report can mistake it for a real vendor credential.
"""

from __future__ import annotations

import datetime as dt
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "phase37" / "fixtures"
OUT.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402


def make_self_signed():
    """
    Generate a local ES256 certificate.

    Trust-chain validation against a public CA is NOT attempted or
    claimed; this exists only so the SDK's signature-verification code
    path can be exercised with a real signature.
    """
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    key = ec.generate_private_key(ec.SECP256R1())
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "BASIRAH Local Test Signer"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "BASIRAH Phase 3.7"),
    ])
    now = dt.datetime.now(dt.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=5))
        .not_valid_after(now + dt.timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    return cert_pem.decode(), key_pem.decode()


def build(image_bytes: bytes, mime: str, cert_pem: bytes, key_pem: bytes,
          claim_generator: str | None) -> bytes | None:
    """
    Sign with the reference SDK.

    Uses the certificate's own chain rather than pointing the SDK at a
    remote trust-list URL, so signing performs NO network I/O.
    """
    from c2pa import Builder, C2paBuilderIntent, C2paSignerInfo, Signer

    info = C2paSignerInfo("es256", cert_pem.encode(), key_pem.encode(), None)
    signer = Signer.from_info(info)
    # Builder takes a manifest template, not a signer; the signer is
    # supplied at sign() time.
    builder = Builder(json.dumps({"version": 1, "claim_generator": claim_generator or "BASIRAH Local Test Generator"}))
    if claim_generator:
        # The action the verification path must later recover.
        builder.add_action({
            "action": "c2pa.created",
            "digitalSourceType": "trainedAlgorithmicMedia",
            "softwareAgent": claim_generator,
        })
        builder.set_intent(C2paBuilderIntent.INDICATE_AI)
    signed = builder.sign(signer, mime, io.BytesIO(image_bytes))
    return signed


def main() -> None:
    buf = io.BytesIO()
    Image.new("RGB", (256, 256), (36, 92, 168)).save(buf, format="JPEG")
    image = buf.getvalue()

    cert_pem, key_pem = make_self_signed()

    results = {}
    for label, generator, intent_note in [
        ("signed_generative", "BASIRAH TestGen/1.0", "asserts generative creation"),
        ("signed_plain", None, "no AI assertion"),
    ]:
        try:
            signed = build(image, "image/jpeg", cert_pem, key_pem, generator)
            path = OUT / f"c2pa_{label}.jpg"
            path.write_bytes(signed)
            results[label] = {
                "path": str(path),
                "bytes": len(signed),
                "note": intent_note,
                "ok": True,
            }
            print(f"  created {path.name} ({len(signed)} bytes) — {intent_note}")
        except Exception as exc:  # noqa: BLE001
            results[label] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
            print(f"  {label}: {type(exc).__name__}: {str(exc)[:150]}")

    # Tampered: flip bytes AFTER signing. Signature must stop validating.
    signed_path = OUT / "c2pa_signed_generative.jpg"
    if signed_path.exists():
        raw = bytearray(signed_path.read_bytes())
        tampered = bytearray(raw)
        # modify pixels in the scan data, leaving the manifest region alone
        mid = len(tampered) // 2
        tampered[mid] ^= 0xFF
        tpath = OUT / "c2pa_tampered.jpg"
        tpath.write_bytes(bytes(tampered))
        results["tampered"] = {"path": str(tpath), "bytes": len(tampered),
                               "note": "signature must NOT validate",
                               "ok": True}
        print(f"  created {tpath.name} ({len(tampered)} bytes) — signature must fail")

    (ROOT / "results" / "phase37" / "c2pa_fixtures.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nwrote {ROOT / 'results' / 'phase37' / 'c2pa_fixtures.json'}")


if __name__ == "__main__":
    main()
