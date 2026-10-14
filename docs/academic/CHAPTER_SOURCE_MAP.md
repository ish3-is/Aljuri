# BASIRAH — Chapter Source Map (Internal Drafting Reference)

> Purpose: a mapping that prevents fabricated academic prose. For each
> Chapter section, point to the BASIRAH evidence / source file.

---

## 1. Chapter 1 — Introduction

| Section | Source of evidence / files |
|---|---|
| 1.1 Problem Statement | `LIMITATIONS.md`, `PROJECT_FACTS.md` (purpose, advisory positioning) |
| 1.2 Aim and Objectives | `PROJECT_FACTS.md` (supported evidence types, languages, deployment constraints) |
| 1.3 Project Scope | `SYSTEM_ARCHITECTURE.md` (frontend/backend scope) |
| 1.4 Contribution | `LIVE_SYSTEM_RESULTS.md`, `METHODOLOGY_EVIDENCE.md` |
| 1.5 Report Outline | This file (CHAPTER_SOURCE_MAP.md) |

---

## 2. Chapter 2 — Background & Literature Review

| Section | Source of evidence / files |
|---|---|
| 2.1 Background / General Concepts | `PROJECT_FACTS.md` (evidence types, languages) |
| 2.2 Core Domain / Technology Overview | `SYSTEM_ARCHITECTURE.md`, `DEPENDENCIES_EVIDENCE.md` |
| 2.2.1 Advantages / 2.2.2 Limitations | `LIMITATIONS.md`, benchmark evidence |
| 2.3 Detailed Technical Concepts | `SYSTEM_ARCHITECTURE.md`, `METHODOLOGY_EVIDENCE.md` |
| 2.4 System Classifications & Deployment Models | `SYSTEM_ARCHITECTURE.md` |
| 2.5 Detection / Processing Techniques & Algorithm Selection | `BENCHMARK_EVIDENCE.md`, `DATASET_EVIDENCE.md` |
| 2.6 Review of Related Work | **PLACEHOLDER** — verified scholarly sources required |
| 2.7 Research Gaps and Project Justification | `METHODOLOGY_EVIDENCE.md`, `PROJECT_FACTS.md` |

> Note: 2.6 Related Work is a **placeholder**. Do not invent papers.

---

## 3. Chapter 3 — Methodology

| Section | Source of evidence / files |
|---|---|
| 3.1 Introduction | `METHODOLOGY_EVIDENCE.md` |
| 3.2 Research Methodology & Framework Separation | `SYSTEM_ARCHITECTURE.md` |
| 3.3 Development Stages | `METHODOLOGY_EVIDENCE.md` (phase chronology) |
| 3.3.1 Time Table / 3.3.2 Gantt Chart | Placeholder (phase chronology → real dates later) |
| 3.4 Data & Evaluation Criteria | `DATASET_EVIDENCE.md`, `BENCHMARK_EVIDENCE.md` |
| 3.5 Summary | This file |

---

## 4. Chapter 4 — System Analysis & Design

| Section | Source of evidence / files |
|---|---|
| 4.1 Introduction | `SYSTEM_ARCHITECTURE.md` |
| 4.2 Requirements Specifications | `REQUIREMENTS_EVIDENCE.md` |
| 4.2.1 Functional Requirements | `REQUIREMENTS_EVIDENCE.md` |
| 4.2.2 Non-Functional Requirements | `REQUIREMENTS_EVIDENCE.md` |
| 4.3 Use Case Diagram | draft (placeholder) |
| 4.4 DFD | draft (placeholder) |
| 4.5 ERD | **NOT APPLICABLE** (no persistent relational data model) |
| 4.6 Sequence Diagrams | draft (placeholder) |
| 4.7 Class Diagram | draft (placeholder) |
| 4.8 Summary | This file |

---

## 5. Chapter 5 — Implementation & Results

| Section | Source of evidence / files |
|---|---|
| 5.1 Introduction | `SYSTEM_ARCHITECTURE.md`, `METHODOLOGY_EVIDENCE.md` |
| 5.2 Offline / Benchmark Evaluation | `BENCHMARK_EVIDENCE.md`, `backend/results/phase37/` |
| 5.3 Live System Evaluation & Demonstration | `LIVE_SYSTEM_RESULTS.md`, browser QA (screenshots) |
| 5.4 Discussion | `PROJECT_FACTS.md` (scientific limitations) |
| 5.5 Summary | This file |

---

## 6. Chapter 6 — Source Code & Appendices

| Section | Source of evidence / files |
|---|---|
| 6.1 Web application / backend | `src/`, `app/`, `package.json`, `requirements.txt` |
| 6.2 Core Model Code | `backend/app/ml`, `reco.py`, `train_url_model.py`, `train_image_models.py` |
| 6.3 Model Training & Evaluation Scripts | `backend/scripts/`, `backend/tools/` |
| 6.4 Database Schema | **NOT APPLICABLE** (no persistent relational model) |
| 6.5 Dependencies | `DEPENDENCIES_EVIDENCE.md`, `package.json`, `requirements.txt` |
| 6.6 Stylesheets & HTML Templates | `src/styles/index.css`, `index.html`, `public/` |

---

## 7. References

| Source | Status |
|---|---|
| Verified scholarly sources | **PENDING** — required for Chapter 2 |
| Basirah project artifacts | `docs/academic/`, `backend/results/phase37/` |
