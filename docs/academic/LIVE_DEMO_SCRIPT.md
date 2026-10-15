# BASIRAH — LIVE DEMO SCRIPT

> Internal drafting reference for the 5–7 minute local demonstration.
> Scientific honesty preserved: no fake real-time result, no "100% authentic",
> no "100% AI-generated". Use advisory terms.

---

## Demo Flow (5–7 minutes)

| # | Step | What to do | Speaker note |
|---|---|---|---|
| 1 | Open BASIRAH locally | Start local backend + dev frontend (`npm run dev` on 5199) | "I'm running the full local mode: a real FastAPI backend on 127.0.0.1:8000." |
| 2 | Show dashboard/home | Land on the home / dashboard | "This is the landing surface — it tells you what the system does." |
| 3 | Analyze suspicious URL | Paste a suspicious URL; wait for the evidence view | "This URL is a real submission. The model produces an advisory distribution, not a fabricated verdict." |
| 4 | Show URL evidence | Show the verdict, URL evidence, coverage | "The verdict carries an uncertainty band — trust/uncertain/adversarial." |
| 5 | Analyze image | Upload/analyze an image | "Now an image. The ensemble gives advisory detector outputs." |
| 6 | Show canonical verdict | Show the three-way verdict | "The canonical verdict is trusted / uncertain / adversarial — it never overclaims." |
| 7 | Show provenance | Show C2PA status/manifest/sig | "Provenance is reported scientifically where C2PA is present." |
| 8 | Show OCR/QR if applicable | Show OCR text or QR decoded destination | "OCR and QR are forensic/content signals; they decode content, they do not certify." |
| 9 | Show Evidence Graph | Render the evidence graph | "Signal sources and correlations are explicit here." |
| 10 | Show Timeline | Render the timeline | "Timeline plays the stage order." |
| 11 | Show report | Show the evidence-oriented report | "The report is evidence-oriented advisory text." |
| 12 | Switch Arabic/English | Toggle EN/AR (RTL) | "The UI is bilingual with full RTL." |
| 13 | Briefly show GitHub Pages showcase | Open `https://ish3-is.github.io/Aljuri/#/analyze` | "This static site is the live showcase — it shows the sample result, no real backend calls." |

---

## Fallback plan if live analysis fails

- If the local backend is down: the UI reports `model_available = false`
  and the heuristic engine carries the assessment. The demo still shows the
  evidence view, provenance, graph/timeline, and report.
- If the frontend dev server is down: serve the built static SPA via
  `npm run build` + a static server, or open the local dev server directly.
- If the live GitHub Pages site is used for the showcase portion: note
  explicitly that it is a **static sample result** with **zero backend calls**
  and **zero HTTP 405** — that is the whole point of the showcase separation.

---

## Demo safety (never do this)

| Never say / do | Use instead |
|---|---|
| Fake real-time result | Real analysis output from the local backend |
| Unverified claim | Advisory verdict + uncertainty band |
| "100% authentic" | "No synthetic indicators detected" / provenance state |
| "100% AI-generated" | "Likely synthetic" / "uncertain" / advisory |
| Saying a detector is certified | "Research-grade, advisory" |
| "The image detector catches everything" | "No evaluated detector met production criteria" |

---

## Suggested timing

| Segment | Approx |
|---|---|
| Title + problem (slides) | 60s |
| System architecture + URL intelligence + image intelligence | 90s |
| Provenance/OCR/QR + evidence fusion + graph/timeline | 90s |
| Live demo (steps 1–11) | 3–4 min |
| GitHub showcase + limitations + contributions | 90s |
| Q&A | 5–7 min |

---

## Demo contingency — if something breaks mid-demo

1. If the URL model is absent or the model is not loaded, the evidence view
   still renders with `model_available = false` (heuristic engine).
2. If the image analysis stack errors, the UI shows the honest error state,
   not a fabricated verdict.
3. Fall back to the **showcase mode** slide and the architecture slide;
   the committee can see both delivery paths clearly.
