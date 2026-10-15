# BASIRAH — COMMITTEE Q&A BANK

> Internal drafting reference for proposal/final presentation and committee
> Q&A. Scientific only — no fabricated results. No supervisor/examiner names
> (placeholders).

---

## 1. Why not claim 99% accuracy?

No evaluated image detector met the production deployment criteria, and the
URL model is advisory by design. BASIRAH reports a three-way canonical verdict
**with an explicit uncertainty band** (trusted / uncertain / adversarial), not
a certified binary. Deploying a classifier that the evaluation shows misses a
non-trivial share of real legitimate URLs as a production "99%" tool would be
an overclaim. The honest statement is: BASIRAH is an advisory evidence pipeline,
not a certified classifier.

---

## 2. Why does cross-corpus performance degrade?

The evaluation corpora are not drawn from the same domain distribution, so a
model that generalises within one corpus can regress on another. The project
tracks this explicitly: cross-corpus generalization is limited and is reported
as a coverage/abstention problem, not hidden. The URL model has an abstention
state that refuses to fabricate a distribution when uncertainty is high.

---

## 3. Why is Detector B shadow-only?

Detector B (CLIP linear probe) is a production *ensemble member* but is
**shadow-only**: it is loaded and contributes signals, but it does not enforce
or block anything, and it is not independently deployed. The evaluation found
that no evaluated detector met the production deployment criteria, so all image
detectors are research/advisory. Detector B's shadow role is preserved so the
ensemble signal is still available for analysis without presenting it as
deployment-grade.

---

## 4. Why no cloud backend?

BASIRAH is local-first because the user is a non-expert making a defensive
assessment; the product is an evidence pipeline, not a SaaS. Keeping real
inference local also means the static GitHub Pages build stays free of
live-inference logic and can serve a safe static showcase. The local backend
(FastAPI on 127.0.0.1:8000) is the only place that runs the actual models.

---

## 5. Why GitHub Pages only for showcase?

GitHub Pages serves a **static** SPA. Providing a real inference path from
GitHub Pages would require shipping runtime models and a backend on a static
host, which would corrupt the demonstration (showcase must never call a live
backend). Instead, GitHub Pages serves a static sample result (`SHOWCASE_RESULT`
via `EvidenceResultView`) clearly marked "DEMO — SAMPLE RESULT". Real analysis
is done locally.

---

## 6. How is BASIRAH different from VirusTotal?

VirusTotal is a third-party aggregate reputation engine (many engines,
server-side, blocklist/oracle-oriented). BASIRAH is an academic advisory
pipeline with **one user's image, URL, or screenshot** in front of a local
evidence service: canonical verdict with uncertainty band, provenance (C2PA
status/manifest/sig), OCR, QR, forensic signals, evidence graph, timeline,
coverage/abstention. It does not claim authenticity, and it never fetches or
executes the user's URL/file.

---

## 7. How do you prevent false claims of authenticity?

The system never claims authenticity. It reports:
- provenance state (`status`, `manifest`, `sig`) where present;
- an advisory verdict with an explicit uncertainty band;
- coverage and abstention accounting.

If C2PA is invalid/missing, that state is reported and the verdict reflects
uncertainty. No "certified", "official forensic certificate", or "legally
verified" wording is used anywhere.

---

## 8. What happens if C2PA signature is invalid?

Provenance reports the invalid/untrusted state. The evidence pipeline preserves
`provenance.status`, `provenance.manifest`, and `provenance.sig` and renders
them. The advisory verdict reflects that the signal is not trusted; no
authenticity claim is made. The goal is scientific reporting of provenance
validity, not reverse engineering the payload.

---

## 9. Why use evidence fusion?

Single-modality numbers are fragile. URL structural features, image forensics,
C2PA provenance, OCR, and QR decode different aspects of the same signal and
can disagree. Fusion aggregates them into one **canonical evidence object**
with a three-way verdict, an explicit uncertainty band, coverage, and
abstention accounting. Fusion is what lets the system say "unclear" instead
of overclaiming a single weak signal.

---

## 10. What is the role of abstention?

Abstention means the system **refuses to fabricate** when uncertainty is high.
The URL model can enter an abstention state (no fabricated distribution), and
the evidence pipeline carries an explicit coverage/abstention accounting. The
correct output when abstention fires is "uncertain", not a confident number.

---

## 11. How do you handle false positives?

Advisory framing, explicit uncertainty band, and a user-review workflow.
No automated blocking. The system reports "caution" / "uncertain" and shows
the supporting signals (provenance, OCR, QR, detectors, coverage) so a human
can review. All image detectors are advisory anyway.

---

## 12. What are the ethical limitations?

- No legal / certified / official forensic certificate.
- No production-grade, legally-defensible image-authenticity service.
- No automatic URL browsing.
- No file execution.
- No claim of authenticity from absence of synthetic indicators.
- Cross-domain generalization is limited.
- No evaluator met production deployment criteria → image AI detection is
  research/advisory.
- Datasets are licensed and excluded; only provenance manifests and audits are
  tracked.

---

## 13. How would you productionize it later?

- Acquire and release a real labelled phishing corpus (pending) and real image
  corpora (licensed, rebuild from recorded URLs + checksums).
- Train/tune the URL model on that corpus and re-run holdout + generalization
  evaluation.
- Formally validate against the deployment criteria; only then consider
  promotion.
- Optionally add a cloud gateway with the same abstention discipline and
  provenance reporting.
- Keep detection advisory unless the evaluation clears the production
  deployment criteria.

---

## 14. Why was v1 retired and v3 selected?

Phase 2E promoted `basirah-url-v3` over the retired `basirah-url-v1`. The
promotion decision is recorded in `backend/models/ACTIVE_MODEL.json` and the
evidence file records:
- real-world legitimate FP of 14: v1 = 10, v3 = 5;
- worst-corpus ROC AUC: v1 = 0.3112, v3 = 0.8481;
- grouped-domain ROC AUC: v1 = 0.5738, v3 = 0.9476;
- semantic phishing false negatives: v1 = 11, v3 = 0.

v3 materially improved real-world FP and held-out phishing recall, so it is
the active production pointer. v1 remains on disk as an optional rollback
artifact but is **not** the active model.

---

## 15. What happens if the model is absent?

The service degrades to the heuristic engine carrying the assessment. The
response reports `model_available = false` and the model component of the risk
score is inactive; no fabricated probability is returned. This is a safeguard,
not a bug.

---

## 16. Why a three-way verdict instead of binary?

Binary "real/fake" overclaims on URL evidence, synthetic-media signals, and
examined media. BASIRAH's scientific position is a three-way canonical verdict
with an explicit uncertainty band: **trusted / uncertain / adversarial**.
"Uncertain" is a feature, not a failure: it means the evidence is inconclusive
and the user should review the signals.

---

## 17. How is provenance verified?

Provenance is verified with `c2pa-python==0.38.0`, preserving scientifically
`provenance.status`, `provenance.manifest`, and `provenance.sig`. The evidence
service reports these where present and renders them. Validity is reported;
absence of a synthetic indicator is not treated as proof of authenticity.

---

## 18. What is the role of OCR/QR?

OCR (Tesseract/EasyOCR fallback) and QR (OpenCV) are **forensic/content
signals**, not credibility certificates. OCR extracts text from an image;
QR decodes the destination encoded in a QR code. They are aggregated into the
evidence payload and feed the canonical verdict and exploration across the
evidence graph/timeline. They decode content — they do not certify the media.

---

## 19. What is the role of abstention? (duplicate of #10 — the committee asked)

See #10. In short: abstention prevents fabrication. When uncertainty is high,
the system says "uncertain" and shows the supporting signals. It never
presents a confident number it cannot defend.

---

## 20. Ethical limitations (summary for slides)

Advisory only. No certification, no legal-verified authenticity, no automatic
enforcement, no file execution, no URL browsing, no overclaiming a solved
image-detection problem. Cross-domain generalization is limited; no evaluator
met production deployment criteria; datasets are licensed/excluded.

---

## 21. What are "research-grade" image detectors?

Detector A (EfficientNet) and Detector B (CLIP linear probe) are evaluated as
research results. They are ensemble members, advisory-only, and none met the
production deployment criteria. They point a user toward a likely-real /
likely-synthetic classification but do not assert legally-verified authenticity.
UnivFD is a research candidate evaluated where applicable and is **not promoted**.

---

## 22. Future work (honest)

- Real labelled phishing corpus and real image corpora (pending, licensed).
- Retrain/tune the URL model on the real corpus and re-run holdout + generalization.
- Formal validation against production deployment criteria; only then consider
  promotion of an image detector.
- Optional cloud gateway with the same abstention discipline and provenance
  reporting.
- Bilingual (EN/AR) report edition if requested.

---

## 23. How would you protect user privacy in a live deployment?

The current design is local-first: the user's file is analysed by the local
FastAPI backend; nothing is exfiltrated. A future cloud gateway would need
explicit consent, short retention, and no storage of the raw artefact unless
the user opted in.

---

## 24. What is the single most important slide to remember?

The system is **advisory**, not certified. Every number is an uncertainty band,
every image detector is research-grade, and "absence of a synthetic indicator"
is not authenticity. That framing is the whole scientific integrity of BASIRAH.
