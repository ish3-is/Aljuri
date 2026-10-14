# Phase 2 — URL Intelligence Engine

> Digital Trust Intelligence — a local, explainable URL analysis pipeline.
>
> **Status:** operational, with one honest gap — **no trained model ships
> with this repository, because no real labelled dataset has been
> acquired.** Real model evaluation is pending dataset acquisition. See
> [ML Pipeline](#7-machine-learning) and [Limitations](#10-limitations).

---

## 1. Purpose

Phase 1 gave BASIRAH an interface and a simulated intelligence layer. That
layer was honest about being simulated, but it could not answer a single
real question about a URL.

Phase 2 replaces the mock for URL signals with a **local analysis
pipeline** that derives every number it reports from the submitted URL
string. The design goal is not detection for its own sake — it is
*explainability*. For any URL, BASIRAH can state:

- which structural indicators fired, and what each one means
- how strong each signal is, as a documented weight
- the combined risk value and the formula that produced it
- how confident the system is in its own assessment
- which axes of Trust DNA were measured, and which do not apply

### Deliberate non-goals

The following are **out of scope for Phase 2** and were not built:

| Not built | Belongs to |
|---|---|
| Live page fetching / crawling | Later phase |
| Browser automation | Later phase |
| WHOIS / DNS reputation | Later phase |
| Google Safe Browsing, VirusTotal | Later phase |
| C2PA / content provenance | Later phase |
| OCR, QR decoding | Phase 4 |
| AI image detection | Phase 3 |

Analysing the URL string alone keeps the system **safe, fast,
reproducible and deployable**. A submitted URL is parsed, never opened.

---

## 2. Architecture

```
                    ┌──────────────────────────────────────┐
  POST /api/        │  api/routes.py                        │
  analyze/url  ───► │  request validation, HTTP status       │
                    └────────────────┬─────────────────────┘
                                     │
                    ┌────────────────▼─────────────────────┐
                    │  services/analyzer.py  (orchestrator)│
                    └───┬───────────┬───────────┬──────────┘
                        │           │           │
        ┌───────────────▼──┐  ┌─────▼────────┐  │
        │ url_analyzer.py  │  │ heuristic_    │  │  ← rule-by-rule
        │ normalise + gate │  │ engine.py     │  │    explainable
        │ (security edge)  │  │ (18 rules)    │  │    findings
        └───────────┬──────┘  └─────┬─────────┘  │
                    │               │            │
        ┌───────────▼──────┐  ┌─────▼─────────┐  │
        │feature_extractor │  │  predictor.py │  │  ← may be
        │   (41 features)  │  │  (sklearn)    │  │    UNAVAILABLE
        └──────────────────┘  └─────┬─────────┘  │
                                     │            │
                          ┌──────────▼────────────▼──────────┐
                          │  risk_engine.py                   │
                          │  model ⊕ heuristics → risk        │
                          └──────────┬───────────────────────┘
                                     │
                          ┌──────────▼───────────────────────┐
                          │  explanation_engine.py            │
                          │  evidence, DNA, timeline, graph  │
                          └──────────────────────────────────┘
```

### Layer responsibilities

| Module | Responsibility | Must not |
|---|---|---|
| `core/config.py` | All thresholds, weights, lexicons | Contain logic |
| `services/url_analyzer.py` | Validation, scheme gate, decomposition | Fetch anything |
| `services/feature_extractor.py` | Deterministic 41-feature vector | Make judgements |
| `services/heuristic_engine.py` | Rule evaluation, weighted aggregation | Emit a verdict |
| `services/risk_engine.py` | Fusion, banding, confidence | Invent thresholds |
| `services/explanation_engine.py` | Bilingual evidence, DNA mapping | Overstate certainty |
| `ml/model_loader.py` | Load/save model bundle | Fabricate a model |
| `ml/predictor.py` | Inference, honest unavailability | Guess when unavailable |
| `ml/dataset.py` | CSV loading, label normalisation | Coerce unknown labels |

---

## 3. Features extracted

41 deterministic features, all pure functions of the URL string. The
order is the **model contract** and is persisted alongside any trained
model, so inference cannot silently drift from training.

### Length
`url_length`, `hostname_length`, `path_length`, `query_length`,
`registered_domain_length`

### Character counts
`dot_count`, `hyphen_count`, `underscore_count`, `slash_count`,
`digit_count`, `special_char_count`, `query_param_count`,
`encoded_char_count`, `double_slash_count`

### Composition ratios
`digit_ratio`, `letter_ratio`, `special_char_ratio`, `encoded_ratio`

### Structure
`subdomain_depth`, `uses_https`, `uses_http`, `is_ip_host`,
`has_at_symbol`, `is_punycode`, `has_port`, `is_abnormal_port`

### Entropy
`url_entropy`, `hostname_entropy`, `path_entropy`,
`registered_domain_entropy`

### Lexical
`suspicious_keyword_count`, `brand_token_count`, `suspicious_tld`

### Derived flags
`is_long_url`, `is_long_hostname`, `is_long_path`,
`is_excessive_subdomain`, `is_excessive_hyphen`,
`is_high_entropy_hostname`, `is_high_digit_ratio`,
`is_suspicious_keyword_combo`

### Entropy measurement

A note on `hostname_entropy`, because the first implementation was wrong
and the correction is instructive for Chapter 5.

Naive Shannon entropy over the raw hostname counts *all* characters. The
separators in `nafath-secure-login` (two hyphens, three dots) therefore
inflate character variety, pushing a purely word-based domain to 4.06
bits/char — while real institutional domains sat at 3.45–3.56, only
0.15 below the firing threshold.

The fix measures entropy over **alphanumeric content only**:

| Hostname | Raw | Alphanumeric only |
|---|---|---|
| `google.com` | 2.65 | 2.42 |
| `en.wikipedia.org` | 3.45 | 3.32 |
| `www.university.edu.sa` | 3.56 | 3.46 |
| `nafath-secure-login.example` | 4.06 | 3.89 |
| `a8f3k2m9x1qz7b4.example` | 4.31 | 4.10 |

Separators are structural, not evidence of randomness.

---

## 4. Heuristic rules

18 rules. Each is independently testable, returns a finding whether or
not it fired, and never produces a verdict.

| Rule ID | Severity | Weight | Fires when |
|---|---|---|---|
| `IP_HOST` | high | 22 | Hostname is a raw IP literal |
| `AT_SYMBOL` | high | 20 | Credentials precede the host |
| `PUNYCODE` | high | 18 | Hostname uses `xn--` encoding |
| `CREDENTIAL_IN_URL` | high | 14 | Credential material in authority or query |
| `EXCESSIVE_ENCODING` | medium | 16 | ≥15% of the URL is percent-encoded |
| `ABNORMAL_PORT` | medium | 12 | Port outside 80/443/8080/8443 |
| `EXCESSIVE_SUBDOMAINS` | medium | 14 | ≥3 subdomain levels |
| `HIGH_ENTROPY_HOSTNAME` | medium | 15 | Alphanumeric entropy ≥3.60 |
| `SUSPICIOUS_KEYWORD_COMBINATION` | medium | 13 | ≥2 credential-themed terms |
| `LONG_HOSTNAME` | medium | 12 | Hostname ≥40 chars |
| `HIGH_DIGIT_RATIO` | medium | 12 | Digits ≥30% of the URL |
| `SUSPICIOUS_TLD` | low | 11 | Suffix is frequently abused |
| `LONG_URL` | low | 10 | URL ≥75 chars |
| `HIGH_ENTROPY_URL` | low | 10 | URL entropy ≥4.30 |
| `EXCESSIVE_HYPHENS` | low | 9 | ≥3 hyphens |
| `LONG_PATH` | low | 8 | Path ≥45 chars |
| `DOUBLE_SLASH` | low | 8 | `//` inside the path |
| `BRAND_LIKE_TOKEN` | medium | 7 | Brand token in a subdomain, not the registered domain |

### Weight calibration

| Band | Weight | Meaning |
|---|---|---|
| 18–25 | strong | Rare in benign URLs |
| 12–17 | meaningful | Corroborating signal |
| 6–11 | weak | Never sufficient alone |
| 3–5 | structural | Informational |

### Keyword handling

A single keyword is **never** evidence. `https://example.com/login` fires
nothing — "login" appears in countless legitimate paths. The rule requires
**two or more distinct terms**, which is what makes
`SUSPICIOUS_KEYWORD_COMBINATION` meaningful.

Percent-encoded keywords are decoded before matching, so
`%6c%6f%67%69%6e` cannot hide "login" from the lexical pass. Arabic lure
terms are included for the same reason.

### Impersonation wording

`BRAND_LIKE_TOKEN` reports a **"possible identity-mismatch pattern"**, not
"This site impersonates X." Establishing intent requires inspecting page
content, which Phase 2 deliberately does not do. The rule also fires only
when the token appears in a *subdomain* rather than the registered domain,
so `paypal.com` is not flagged while `paypal-secure.example.com` is.

---

## 5. Risk fusion

```
model_risk      ∈ [0, 100]   (0 when no model is available)
heuristic_risk  ∈ [0, 100]

final_risk = w_model × model_risk + w_heuristic × heuristic_risk
trust_score = 100 − final_risk
```

| Setting | Value | Rationale |
|---|---|---|
| `model_weight` | 0.45 | Statistical signal, but generalises poorly to unseen domains |
| `heuristic_weight` | 0.55 | A triggered rule is a directly inspectable fact about this URL |
| `heuristic_saturation` | 100 | Weight sums above 100 do not exceed 100 risk |
| `caution_threshold` | 30 | — |
| `high_risk_threshold` | 60 | Requires substantial corroboration |

When no model is loaded, `w_model = 0` and `w_heuristic = 1.0`. The
heuristics carry full weight rather than being diluted against an absent
signal, and the response states which formula ran.

### Evidence floors

Two floors prevent an *accident of arithmetic* from deciding a verdict.
Both are set **at** the caution boundary, so they can lift a score into
caution but never into high risk:

| Floor | Effect |
|---|---|
| `min_high_severity_score = 30` | Any high-severity rule reaches caution |
| `min_corroborating_score = 30` (≥2 rules) | Any two corroborating indicators reach caution |

**Why these exist.** The first implementation summed weights with no
floor. Two genuine indicators on `nafath-secure-login.example` summed to
28 against a threshold of 30 — two points of arithmetic luck reporting
corroborated evidence as "trusted". Likewise a raw-IP host (weight 22)
would have been called trusted. Floors make the band reflect a judgement
about the evidence rather than a rounding accident.

### The central safety property

**No single rule can produce a high-risk classification.** Enforced
structurally in `risk_engine.py` and verified by tests that assert it
across ten isolated single-indicator URLs. Even a model returning
`P(phishing) = 1.0` with zero fired rules cannot convict.

This is what makes the system's probabilistic claims defensible: a
high-risk verdict always means *several independent signals agreed*.

### Confidence

Confidence (0–100) expresses **evidence strength**, not risk. It rises
with corroboration, high-severity findings, model agreement and distance
from a decision boundary — and is explicitly **penalised by 10 points when
no model is available**, because the system is more uncertain without a
trained classifier and saying so is part of being academically honest.

---

## 6. API

Base URL: `http://localhost:8000` (development).
Interactive docs: `http://localhost:8000/docs`

### `GET /api/health`

```json
{
  "status": "ok",
  "service": "BASIRAH URL Intelligence Engine",
  "version": "2.0.0",
  "phase": "Phase 2 — URL Intelligence",
  "model_available": false,
  "heuristic_rules": 18,
  "feature_count": 41
}
```

### `POST /api/analyze/url`

Request: `{"url": "https://example.com"}`

Response (abridged):

```json
{
  "isMock": false,
  "source": "live",
  "engine": "basirah-url-intelligence",
  "engineVersion": "2.0.0",
  "signal": { "kind": "url", "valueEn": "https://example.com", "valueAr": "https://example.com" },
  "trustScore": 70.0,
  "riskLevel": "caution",
  "confidence": 41.5,
  "dna": { "domain": 30, "identity": 45, "behavior": 30, "synthetic": null, "provenance": null },
  "graph": { "nodes": [], "edges": [] },
  "timeline": [],
  "primarySignal": { "titleEn": "...", "titleAr": "...", "bodyEn": "...", "bodyAr": "..." },
  "secondarySignals": [],
  "lanes": ["url_intelligence", "identity", "metadata"],
  "durationMs": 12.4,

  "normalizedUrl": "https://nafath-secure-login.example",
  "modelAvailable": false,
  "modelNote": "No trained model available; ...",
  "heuristicFindings": [],
  "riskBreakdown": {
    "modelRisk": 0.0, "heuristicRisk": 30.0, "finalRisk": 30.0,
    "modelWeight": 0.0, "heuristicWeight": 1.0,
    "formula": "final_risk = 1.0 x heuristic_risk = 30.0 (...)"
  },
  "featureObservations": []
}
```

### `GET /api/model/info`

Transparency metadata: model name, version, feature count, training
metrics. **Exposes no filesystem paths.** Returns `metrics: null` when no
model has been trained — never invented numbers.

### Errors

| Situation | Status | Code |
|---|---|---|
| `javascript:`, `file://`, `data:`, `ftp:` | 422 | `unsupported_scheme` |
| URL > 2048 chars | 422 | `url_too_long` |
| No hostname | 422 | `missing_host` |
| Invalid port | 422 | `invalid_port` |
| Missing `url` field | 422 | `validation_error` |

---

## 7. Machine learning

### Status: pipeline complete, no model shipped

The training pipeline is implemented and verified end to end. **No
trained model is included**, because none can be honestly trained: no real
labelled dataset has been acquired.

> **Real model evaluation is pending dataset acquisition.**

### Candidates

| Model | Rationale |
|---|---|
| Logistic Regression | Fully interpretable coefficients — relevant for explainability |
| Random Forest | Handles non-linear interactions, robust to scaling |
| Gradient Boosting | Typically strongest on tabular lexical features |

### Leakage controls

- Features extracted from the URL string only
- **Stratified** train/test split on the label
- `StandardScaler` inside the `Pipeline`, fitted on the training fold only
- Duplicates removed before splitting
- `random_state = 42` throughout

### Selection rule

**Maximum F1, ties broken by recall.** Accuracy is deliberately *not* the
selection metric: on a 90/10 split a model that never predicts phishing
scores 90% accuracy while catching nothing.

### Usage

```powershell
.venv\Scripts\python.exe -m scripts.train_url_model --data datasets\<file>.csv
.venv\Scripts\python.exe -m scripts.evaluate_url_model
```

Artefacts written to `models/`: the estimator, its feature order, and a
metadata JSON containing metrics and dataset provenance.

### Development fixture

`datasets/dev_fixture_urls.csv` holds 20 hand-written rows that exist only
to prove the pipeline executes. The trainer **refuses to use it** without
`--allow-dev-fixture`, and marks any resulting model `evaluated: false`
with an explicit warning. It produced 1.0000 across every metric on 20
rows — precisely the result that must never be reported as evidence of
anything.

---

## 8. Frontend integration

```
src/features/analysis/providers.ts
├── AnalysisProvider          interface
├── mockAnalysisProvider      images / screenshots / QR
├── ApiAnalysisProvider       URLs → FastAPI
└── resolveProvider(kind)     routing
```

URLs go to the real backend; images keep the Phase 1 mock so the Phase 1
demo is unbroken until Phase 3. **A provider failure never falls back to
mock data** — the UI shows an explicit error, because a trust product
that fabricates intelligence when its engine is unreachable would
contradict its own premise.

Configuration is centralised in `VITE_API_BASE_URL` (see `.env.example`).
No component hardcodes a hostname.

### Contract changes from Phase 1

Two minimal, honest changes:

1. **`DnaValue = number | null`.** A URL has no synthetic-media or
   provenance evidence. Those axes return `null` and the UI renders
   `N/A` — not `0`, which would present an unmeasured axis as a measured
   score of zero. The UI also states "3 of 5 axes measured".
2. **`InvestigationState` gains `'error'`.** A failed analysis is a
   distinct terminal state, not a silent empty result.

---

## 9. Evaluation methodology

Prepared for Chapter 7. To be executed once a real dataset exists.

| Metric | Why it matters here |
|---|---|
| Accuracy | Reported, **never used for selection** |
| Precision | How many flagged URLs were genuinely phishing |
| **Recall** | How many phishing URLs were caught — the costlier error |
| **F1** | Primary selection metric |
| ROC-AUC | Threshold-independent ranking quality |
| False positive rate | Legitimate URLs wrongly flagged — the trust cost |
| False negative rate | Phishing URLs missed — the safety cost |

Recommended addition beyond the standard set: a **time-based split** when
the dataset carries collection dates. A random split lets the model see
near-duplicates of its training rows, which inflates apparent
performance relative to genuinely new URLs.

Heuristic-only evaluation is already possible without any dataset, using
the labelled expectations in `tests/test_calibration.py`.

---

## 10. Limitations

1. **No trained model ships.** All risk currently derives from heuristics
   alone, and every response says so. This is the single largest gap.
2. **No real dataset evaluation.** No accuracy, precision, recall, F1 or
   ROC-AUC figure for this system exists yet. None is claimed.
3. **URL string only.** Cannot see page content, redirects, certificate
   state, hosting history or DNS age. Many phishing sites use URLs that
   look structurally benign, so **false negatives are expected**.
4. **Keyword lists are hand-curated**, not learned, and drift as attackers
   adapt.
5. **Brand detection is a small fixed list** (~30 tokens), not a brand
   database. It is a Phase 2 approximation.
6. **No adversarial robustness testing.** An attacker aware of these
   features can construct URLs that evade them. Relevant for Chapter 8.
7. **English- and Arabic-language keywords only.** Other languages are not
   covered.
8. **`tldextract` uses its bundled public-suffix snapshot.** Newer TLDs
   may be unrecognised, degrading registered-domain decomposition.
9. **Heuristic weights are reasoned, not optimised.** They were set from
   the shape of ordinary navigational URLs. A dataset would allow
   principled calibration, and would likely change them.

---

## 11. Future improvements

**Immediate (unblocks the largest gap)**
1. Acquire a real labelled dataset; record licence, provenance, date.
2. Train, evaluate, and calibrate heuristic weights against it.
3. Report metrics in Chapter 7 with the split strategy stated.

**Short term**
4. Time-based train/test split for an honest generalisation claim.
5. Character n-gram TF-IDF features to complement lexical features.
6. Per-rule precision analysis to retire rules that never help.
7. Confidence calibration against observed correctness.

**Medium term**
8. Redirect-chain following, still without rendering content.
9. Certificate and TLS-derived features.
10. Brand registry with regional coverage.
11. Rate limiting and request logging for the public API.

**Later phases**
12. Phase 3: synthetic-media signals on image inputs.
13. Phase 4: multimodal correlation, QR and OCR.
14. Phase 5: fusion across all evidence types.

---

## Appendix A — Reproducing the verification

```powershell
cd D:\MDR\Aljuri-Greadute-Project\backend
.venv\Scripts\python.exe -m pytest tests\ -q          # 192 tests
```

```powershell
cd D:\MDR\Aljuri-Greadute-Project\basirah
npm run build
npx eslint .
```

End-to-end: start the backend, start the frontend, submit a URL, and
confirm the result carries `isMock: false` and a `Live analysis` badge.

## Appendix B — Test coverage

| File | Tests | Focus |
|---|---|---|
| `test_url_analyzer.py` | 34 | Normalisation, scheme rejection, IPv4/IPv6, punycode, invisible characters |
| `test_feature_extractor.py` | 30 | Entropy, feature contract stability, lexical features |
| `test_heuristics_and_risk.py` | 33 | Rule registry, per-rule firing, no-single-rule-convict, fusion |
| `test_calibration.py` | 18 | Entropy separation, evidence floors, monotonicity, determinism |
| `test_dataset.py` | 20 | Label vocabularies, cleaning, no-shipped-model guard |
| `test_api.py` | 32 | HTTP surface, contract fields, rejections, no-verdict language |

## Appendix C — Language policy

All user-facing text is probabilistic. Phrases used and phrases refused:

| Used | Refused |
|---|---|
| "Multiple indicators contributed to a risk value of X" | "This URL is malicious" |
| "A pattern consistent with imitating an organisation" | "This site impersonates X" |
| "The classifier assigned a probability of X, one input among several" | "The model determined this is phishing" |
| "No strong structural indicators were observed" | "This URL is safe" |

A test asserts the refused phrasings never appear in any response.
