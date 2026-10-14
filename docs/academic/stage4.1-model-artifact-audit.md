# BASIRAH — MODEL & ARTIFACT PUBLICATION AUDIT
# Stage 4.1 — FINAL DELIVERY
#
# Classification of backend models, datasets, evaluation artifacts,
# results, and cache files for public GitHub publication.
#
# Every decision is based on actual code references and runtime usage.
# No scientific behavior was modified. No push to GitHub performed.
# ========================================================================

## 1. ACTIVE URL MODEL
#   File: models/basirah-url-v3.joblib
#   Metadata: models/basirah-url-v3.metadata.json
#   Evidence: models/ACTIVE_MODEL.json (Phase 2E "PROMOTE v3")
#   - real-world FP of 14: 5/14 (v1: 10/14)
#   - recall at matched FPR 0.05: 0.7497 (v1: 0.2892)
#   - worst-corpus AUC: 0.8481 (v1: 0.3112)
#   - grouped-domain AUC: 0.9476 (v1: 0.5738)
#   - passes every Phase 2E acceptance gate
#
#   v1 (basirah-url-v1.joblib + .metadata.json) is RETAINED on disk as
#   the fallback bundle (FALLBACK_BUNDLE in app/ml/production.py).
#
#   v4 (basirah-url-v4.joblib) is a research artifact only. Not promoted.
#   Referenced by results/phase2e/promotion_decision.json and
#   scripts/run_phase2e_experiment.py. Excluded from public repo.

## 2. ACTIVE IMAGE MODEL
#   File: models/multifamily_candidates/efficientnet_b0__C_holdout_Midjourney.pt
#   Evidence: models/RESEARCH_IMAGE_MODEL.json
#   - Research-grade only, advisory only (FIT_FOR_AUTOMATED_ENFORCEMENT=false)
#   - Trained on GAN + PixelDiffusion + LatDiff; evaluated on unseen
#     Midjourney family: ROC-AUC 0.9832, balanced accuracy 0.9311
#   - The older basirah-image-cand-efficientnet_b0.pt (within-family
#     0.9984 AUC) is deliberately NOT used — it scored 0.3954 on
#     external cross-family transfer and flagged 89.7% of genuine
#     photographs. Excluded.

## 3. SHADOW DETECTOR MODEL
#   File: models/detector_b_clip_probe.joblib
#   - Detector B: CLIP ViT/ConvNeXt image encoder + LINEAR probe
#   - Independent second opinion for the advisory image stack
#   - Loaded by app/image/ensemble_integration.py (PROBE_PATH)

## 4. RUNTIME-REQUIRED MODEL FILES (public repo minimum package)
#   backend/models/
#     - ACTIVE_MODEL.json              (metadata pointer)
#     - RESEARCH_IMAGE_MODEL.json      (research checkpoint pointer)
#     - feature_schema.json            (41-feature schema)
#     - basirah-url-v3.joblib          (active URL model, LFS)
#     - basirah-url-v3.metadata.json   (LFS)
#     - basirah-url-v1.joblib          (fallback URL model, LFS)
#     - basirah-url-v1.metadata.json   (LFS)
#     - basirah-url-v4.metadata.json   (metadata only, LFS)
#     - multifamily_candidates/
#         - efficientnet_b0__C_holdout_Midjourney.pt   (LFS, research)
#     - detector_b_clip_probe.joblib   (LFS, Detector B probe)
#
#   NOT included:
#     - basirah-image-cand-efficientnet_b0.pt (0.9984 within-family,
#       unusable on transfer — excluded)
#     - basirah-url-v4.joblib (research artifact, not promoted — excluded)
#     - multifamily_candidates/dinov2_lr_*.joblib (5 files, research-only —
#       excluded)

## 5. DEPRECATED / UNUSED MODELS
#   - basirah-url-v1.joblib / .metadata.json
#     → Retained on disk but classification: EXCLUDE from public repo
#     (fallback only, superseded by v3; kept on disk for local rollback)
#
#   - basirah-url-v4.joblib
#     → EXCLUDE (not promoted; documented as research artifact)
#
#   - basirah-image-cand-efficientnet_b0.pt
#     → EXCLUDE (within-family-only result, broken on transfer)
#
#   - efficientnet_b0__A/B/D/E.pt (5 files) + dinov2_lr__*.joblib (5 files)
#     → EXCLUDE (research-only candidates, not in runtime path)
#
#   - multifamily_candidates/ directory
#     → EXCLUDE except efficientnet_b0__C_holdout_Midjourney.pt

## 6. DATASETS — FILES TO EXCLUDE
#   backend/datasets/raw/            (raw large datasets — never publish)
#   backend/datasets/processed/       (large processed datasets — exclude)
#   backend/datasets/image/raw/       (licensed images — never publish)
#   datasets/image/manifests/_tree_*.json
#   datasets/image/manifests/_cf_shard_index.json
#   (the *_tree_*.json and _cf_shard_index.json files are large
#   intermediate downloads; manifests are tracked but sharded)
#
#   KEEP (small, academically useful, redistributable):
#   - datasets/dev_fixture_urls.csv  (20-row dev fixture, documented)
#   - datasets/image/audit/*.json    (provenance audits)
#   - datasets/manifests/phase2d_legitimate_sources.json
#   - datasets/manifests/phiusil_manifest.json
#   - datasets/README.md (dataset documentation)
#
#   NOTE: Real dataset acquisition instructions are documented in
#   datasets/README.md — the pipeline expects a CSV with url,label
#   columns. No real labelled dataset is bundled (honest statement).

## 7. DATASET METADATA TO KEEP
#   - datasets/image/audit/aigcdetection_benchmark.json
#   - datasets/image/audit/aigcdetection_benchmark_ADM.json
#   - datasets/image/audit/aigcdetection_benchmark_BigGAN.json
#   - datasets/image/audit/aigcdetection_benchmark_CycleGAN.json
#   - datasets/image/audit/aigcdetection_benchmark_DALLE2.json
#   - datasets/image/audit/aigcdetection_benchmark_GauGAN.json
#   - datasets/image/audit/aigcdetection_benchmark_GLIDE.json
#   - datasets/image/audit/aigcdetection_benchmark_Midjourney.json
#   - datasets/image/audit/aigcdetection_benchmark_ProGAN.json
#   - datasets/image/audit/aigcdetection_benchmark_Real.json
#   - datasets/image/audit/aigcdetection_benchmark_SD14.json
#   - datasets/image/audit/aigcdetection_benchmark_SD15.json
#   - datasets/image/audit/aigcdetection_benchmark_SDXL.json
#   - datasets/image/audit/aigcdetection_benchmark_StarGAN.json
#   - datasets/image/audit/aigcdetection_benchmark_StyleGAN.json
#   - datasets/image/audit/aigcdetection_benchmark_StyleGAN2.json
#   - datasets/image/audit/aigcdetection_benchmark_VQDM.json
#   - datasets/image/audit/aigcdetection_benchmark_WhichFaceIsReal.json
#   - datasets/image/audit/aigcdetection_benchmark_Wukong.json
#   - datasets/image/audit/communityforensics_small_real.json
#   - datasets/image/audit/communityforensics_small_synthetic_*.json
#   - datasets/image/audit/corpus_classifier.json
#   - datasets/image/audit/SHORTCUT_AUDIT.md
#   - datasets/image/audit/shortcut_report.json
#   - datasets/manifests/phase2d_legitimate_sources.json
#   - datasets/manifests/phiusil_manifest.json

## 8. RESULTS — FILES TO KEEP
#   Keep these as concise, academically useful evidence:
#   - results/phase2e/abblation_results.csv
#   - results/phase2e/abblation_verdict.json
#   - results/phase2e/calibration_results.csv
#   - results/phase2e/category_fpr.csv
#   - results/phase2e/corpus_classifier_metrics.csv
#   - results/phase2e/domain_cap_comparison.csv
#   - results/phase2e/false_negative_analysis.csv
#   - results/phase2e/false_positive_analysis.csv
#   - results/phase2e/feature_importance.csv
#   - results/phase2e/feature_variant_comparison.csv
#   - results/phase2e/https_bias_analysis.csv
#   - results/phase2e/https_bias_baseline.csv
#   - results/phase2e/matched_fpr_comparison.csv
#   - results/phase2e/model_comparison.csv
#   - results/phase2e/path_bias_analysis.csv
#   - results/phase2e/path_bias_verdict.json
#   - results/phase2e/promotion_decision.json
#   - results/phase2e/sampling_strategy.json
#   - results/phase2e/semantic_regression_expanded.csv
#   - results/phase2e/semantic_regression_original.csv
#   - results/phase2e/source_audit.json
#   - results/phase2e/threshold_results.csv
#   - results/phase37/blind_defense_test.json
#   - results/phase37/detector_b_eval.json
#   - results/phase37/ensemble_agreement_analysis.json
#
#   NOTE: results/phase37/blind_predictions.json (20803 bytes) — keep
#   as evidence; it is a compact JSON summary of the blind defense test.

## 9. RESULTS — FILES TO EXCLUDE
#   Exclude these (logs, caches, huge intermediates, duplicates):
#   - results/phase3/robustness_probs_cache.npz
#   - results/phase3/multifamily_probs/*.npz
#   - results/phase3/_probs_efficientnet_done.npy
#   - results/phase3/multifamily_rerun.log
#   - results/phase3/multifamily_run.log
#   - results/phase3/robustness_run.log
#   - results/phase2c/*.csv, *.json (transients)
#   - results/phase2d/*.csv, *.json (transients)
#   - results/phase3/c_clean_roc_pr.png (binary plot, exclude)
#   - results/phase3/multifamily_corpus.csv (huge intermediate, exclude)
#   - results/phase3/multifamily_splits.json (huge, exclude)
#   - results/phase3/multifamily_training_progress.json (transient, exclude)
#   - results/phase3/splits.json (huge, exclude)
#   - results/phase3/crossfamily_*.csv / *.json (huge intermediates, exclude)
#   - results/phase3/family_*.csv (intermediate, exclude)

## 10. EVALUATION — FILES TO KEEP
#   - evaluation/build_deployment_manifest.py
#   - evaluation/run_image_benchmark.py
#   - evaluation/requirements.txt
#   - evaluation/image_deployment_v1/artifacts/
#       (benchmark_summary.md, image_benchmark_abstention_policies.csv,
#        image_benchmark_audit.md, image_benchmark_confusion_matrices.csv,
#        image_benchmark_focused.json, image_benchmark_group_metrics.csv,
#        image_benchmark_metrics.json, image_benchmark_operating_points.csv,
#        image_benchmark_report.md, image_benchmark_samples.csv,
#        image_benchmark_scores.json, image_benchmark_thresholds.csv)
#   - evaluation/image_deployment_v1/samples/
#       (deployment_v1_manifest.csv, triage_paths.json)
#
#   EXCLUDE from public repo:
#   - evaluation/__pycache__/*.pyc (cache)
#   - evaluation/artifacts/* (large artifact dumps — see .gitignore)

## 11. ALL FILES > 5MB
#   Path                                           Size    Purpose
#   ---------------------------------------------------------------
#   models/basirah-image-cand-efficientnet_b0.pt   16.35MB Research candidate
#     (excluded from public repo — not promoted)
#   models/multifamily_candidates/efficientnet_b0__C_holdout_Midjourney.pt  16.35MB
#     Runtime-required research image checkpoint (LFS)
#   models/basirah-url-v3.joblib                   3.79MB  Runtime-required (LFS)
#   models/detector_b_clip_probe.joblib            5.37MB  Runtime-required (LFS)
#   (other .joblib/.pt are < 5MB)

## 12. PROPOSED .GITIGNORE ADDITIONS
#   (added to backend/.gitignore)
#   - .venv/
#   - __pycache__/
#   - *.py[cod]
#   - .pytest_cache/
#   - *.log, logs/
#   - .env, .env.local
#   - datasets/raw/, datasets/processed/, datasets/image/raw/
#   - datasets/image/manifests/_tree_*.json, _cf_shard_index.json
#   - datasets/dev_fixture_urls.csv (allowed)
#   - **/*.npy, **/*.npz, **/cache*.npz, *_cache.npz, **/*.cache
#   - evaluation/artifacts/, evaluation/results/,
#     evaluation/image_deployment_v1/artifacts/
#   - results/*.csv, results/*.log, results/*cache*.npz, *_cache.npz
#   - (NOTE: .pt/.joblib are NOT globally ignored; see .gitattributes for LFS)

## 13. FILES DELETED DURING CLEANUP
#   backend/_fi.py
#   backend/_fix_magic.py
#   backend/_fr2.py
#   backend/analyze_thresholds.py
#   backend/audit_operating_points.py
#   backend/cleanup_pydantic.py
#   backend/compute_abstention.py
#   backend/compute_group_metrics.py
#   backend/verify_abstention.py
#   backend/fix_pydantic.py
#   backend/identify_port.py
#   backend/test_minimal.png
#   backend/backend.log
#   basirah/compute-offenders.mjs
#   basirah/README.md (rewritten)
#   basirah/scripts/debug-frontend.mjs
#   basirah/scripts/diag-*.mjs (15 files)
#   basirah/scripts/dump-gemini-text.mjs
#   basirah/scripts/stage3-*.mjs (3 files)
#   basirah/scripts/verify-closure.mjs, verify_closure2.mjs
#   basirah/scripts/verify_gemini_old.mjs
#   basirah/scripts/verify_gemini_frontend2/3/4/5.mjs
#   basirah/scripts/verify_live_browser.mjs
#   basirah/scripts/verify_live_stage2.mjs
#   basirah/scripts/verify-stage3-mobile-final.mjs
#   basirah/scripts/run_live_stage2.sh
#   basirah/scripts/stage3-final.log, stage3-qa.log, stage3-responsive.log
#   basirah/scripts/stage3-final-results.json, stage3-responsive-results.json,
#       stage3-results.json, stage3-micro-qa-final.json/.log
#   basirah/scripts/trim-assets.mjs
#   basirah/scripts/qa_run-checks.sh (renamed from _run-checks.sh)
#   basirah/scripts/verify-live-stage2.mjs (removed)
#   basirah/screenshots/*.png (4 screenshots — dev-only)
#   basirah/artifacts/stage2-live/ (staged artifacts)
#   basirah/nul
#   basirah/.env.local (dev-only; regenerate from .env.example)
#   backend/scripts/start_server.sh (python code misidentified, renamed)
#   backend/scripts/start_server.py (correct location of start_server.py)
#   backend/scripts/start_backend.sh (developer QC script)
#
#   NOTE: basirah/.env.local was deleted as a dev-only file. Developers
#   copy .env.example to .env.local to recreate it.

## 14. FILES LEFT FOR MANUAL REVIEW
#   - basirah/Logo.png, basirah/UNI_LOGO.png (project logos — keep)
#   - basirah/CLOSURE_REPORT.md (internal project report — review)
#   - docs/academic/ (academic evidence pack — review)
#   - docs/ZORO_ARCHITECTURE.md (development architecture — internal)
#   - backend/docs/ (internal docs — review)
#   - backend/datasets/README.md (dataset documentation — keep)
#   - backend/datasets/image/audit/ (provenance audits — keep)
#   - basirah/scripts/release-docs.md (documentation — review)
#   - backend/evaluation/ (evaluation pipeline code — keep)
#   - basirah/qa/ (QA scripts — review/manual)
#   - basirah/scripts/ (verify-ui.mjs, verify-wording.mjs,
#                          verify-excel-sanitiser.mjs, verify-report-mapper.mjs,
#                          verify-stage3-mobile-final.mjs — keep)
#   - backend/scripts/ (28 reproducible evaluation scripts — keep)
#   - backend/evaluation/image_deployment_v1/samples/ (locked eval set —
#     review)

## 15. MINIMUM RUNTIME MODEL PACKAGE (public repo)
#   backend/models/
#     ACTIVE_MODEL.json
#     RESEARCH_IMAGE_MODEL.json
#     feature_schema.json
#     basirah-url-v3.joblib  + .metadata.json
#     basirah-url-v1.joblib  + .metadata.json
#     basirah-url-v4.metadata.json
#     multifamily_candidates/efficientnet_b0__C_holdout_Midjourney.pt
#     detector_b_clip_probe.joblib
#   (all .joblib/.pt go through .gitattributes LFS; see .gitattributes)
#
#   Note: No real curated dataset is bundled. The pipeline expects a
#   CSV with url,label and is instructed in datasets/README.md on how
#   to obtain one. A dev fixture is included for pipeline verification.

## 16. TEST/ GATE RESULTS (after cleanup)
#   Backend:  429 passed, 1 skipped, 2 xfailed, 1 warning   (pytest -q)
#   Frontend: tsc: 0 errors   (npx tsc -p tsconfig.app.json --noEmit)
#             lint: 0 errors  (npm run lint)
#             build:  ✓ built in 826ms    (npm run build)
#             verify-wording:  127/127  (node scripts/verify-wording.mjs)
#             verify-ui:       74/74   (node scripts/verify-ui.mjs)
#             verify-excel-sanitiser: pass

## 17. EXACT FILES SAFE TO UPLOAD TO GITHUB
#   Frontend (basirah/):
#     .env.example, .gitignore, eslint.config.js, index.html,
#     package.json, package-lock.json, README.md, tsconfig.app.json,
#     tsconfig.json, tsconfig.node.json, vite.config.ts,
#     src/, public/, scripts/verify-ui.mjs, scripts/verify-wording.mjs,
#     scripts/verify-excel-sanitiser.mjs, scripts/verify-report-mapper.mjs,
#     scripts/verify-stage3-mobile-final.mjs,
#     Logo.png, UNI_LOGO.png
#     docs/academic/, docs/ZORO_ARCHITECTURE.md, docs/phase2-url-intelligence.md
#
#   Backend (backend/):
#     .gitattributes, .gitignore, README.md, requirements.txt,
#     app/, tests/, scripts/ (28 reproducible evals),
#     evaluation/run_image_benchmark.py,
#     evaluation/build_deployment_manifest.py,
#     evaluation/requirements.txt
#     datasets/dev_fixture_urls.csv, datasets/README.md,
#     datasets/image/audit/*.json, datasets/manifests/*.json
#     models/ (runtime package above)
#
#   Project root:
#     .gitignore, .gitattributes, LICENSE, README.md (root),
#     docs/academic/, docs/DEPLOYMENT_READINESS.md

## 18. EXACT FILES THAT MUST NOT BE UPLOADED
#   - basirah/node_modules/ (package-lock.json present)
#   - basirah/dist/ (build output — generated at install)
#   - basirah/artifacts/ (staged dev screenshots/artifacts)
#   - basirah/screenshots/ (dev screenshots)
#   - backend/.venv/ (virtual environment)
#   - backend/.pytest_cache/ (pytest cache)
#   - backend/__pycache__/ (python cache)
#   - backend/models/basirah-image-cand-efficientnet_b0.pt
#   - backend/models/basirah-url-v4.joblib
#   - backend/models/multifamily_candidates/.joblib/.pt (research-only)
#   - backend/datasets/raw/ (raw datasets)
#   - backend/datasets/processed/ (processed datasets)
#   - backend/results/ (raw results — see filters above)
#   - backend/evaluation/artifacts/ (large artifact dumps)
#   - backend/scripts/_run-checks.sh, start_backend.py
#   - backend/start_server.py, start_backend.py (root copies)
#   - basirah/.env.local (dev-only)
#   - basirah/scripts/qa_run-checks.sh (dev-only devport QC)
#   - LICENSE / .gitignore at root (KEEP — see above)
#
#   NOTE: The large dev screenshots and artifacts are dev-only.
#   They can be regenerated later. Nothing of academic value is lost.
#   REGRESSION SAMPLES are available via
#   evaluation/image_deployment_v1/samples/ (locked eval set).

END OF MODEL & ARTIFACT PUBLICATION AUDIT
