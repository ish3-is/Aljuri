/**
 * FORBIDDEN-WORDING TEST (Phase 3.7)
 *
 * Run: node scripts/verify-wording.mjs
 *      (also wired as `npm run verify:wording`)
 *
 * WHY THIS IS AN AUTOMATED TEST AND NOT A CODE REVIEW STEP
 *
 * The six phrases below are the exact ways this product can lie
 * about its own output. Every one of them is individually plausible
 * copy that a well-meaning edit could introduce, and every one of them
 * converts a probabilistic measurement into a guarantee:
 *
 *   "100% Authentic"      a probability rendered as certainty, and a
 *                          number no ensemble in this project produces
 *   "Verified Real"       the same, with "verified" attached — the one
 *                          word that is reserved for a validated C2PA
 *                          signature and nothing else
 *   "Definitely Genuine"  an absolute where only a likelihood exists
 *   "100% AI"             symmetric overclaim in the other direction
 *   "Guaranteed Safe"     a safety promise the platform cannot make in
 *                          any domain, phishing included
 *
 * A review checklist catches these once. This catches them forever,
 * including in the string a component builds at runtime from a
 * template literal.
 *
 * WHAT IS SCANNED
 *
 * Both the SOURCE and the BUILT OUTPUT, because the two catch
 * different failure modes:
 *
 *   source  — catches a forbidden phrase in a string literal, a
 *             translation entry, or a comment. Catches it before it
 *             ever reaches a bundle.
 *   dist    — catches a phrase assembled by string concatenation at
 *             runtime, which no source grep can see because the
 *             literal parts are individually innocent.
 *
 * Exclusions are narrow and deliberate: this very file (it has to
 * name the phrases to forbid them) and any line that is explicitly a
 * check for them.
 */

import fs from 'node:fs'
import path from 'node:path'

/**
 * The forbidden set.
 *
 * Matching is case-insensitive and whitespace-tolerant, because "100%
 * authentic" and "100%  Authentic" are the same claim.
 */
const FORBIDDEN = [
  '100% authentic',
  'verified real',
  'definitely genuine',
  '100% ai',
  'guaranteed safe',
  'authenticity %',
  'realness %',
  'verified %',
]

/** Files whose content is the ban list itself, not product copy. */
const SELF = new Set(['verify-wording.mjs'])

const SOURCE_ROOTS = ['src']
const SOURCE_EXT = /\.(ts|tsx|json|html|css|js|mjs)$/

let failures = 0
let checks = 0
let scanned = 0

function report(file, lineNumber, line, phrase) {
  failures += 1
  console.error(
    `FAIL  ${file}:${lineNumber} contains forbidden wording ${JSON.stringify(phrase)}`,
  )
  console.error(`      ${line.trim().slice(0, 120)}`)
}

/** A line that documents or asserts the ban, rather than committing it. */
function isGuardLine(line) {
  return (
    line.includes('FORBIDDEN') ||
    line.includes('verify-wording') ||
    line.includes('forbidden wording')
  )
}

function scanText(label, text) {
  checks += 1
  const lines = text.split('\n')
  lines.forEach((line, index) => {
    if (isGuardLine(line)) return
    const haystack = line.replace(/\s+/g, ' ').toLowerCase()
    for (const phrase of FORBIDDEN) {
      // A normalised haystack still contains the original spacing
      // between words, so compare against the same normalisation.
      if (haystack.includes(phrase.replace(/\s+/g, ' '))) {
        report(label, index + 1, line, phrase)
      }
    }
  })
}

console.log('=== 1. FORBIDDEN WORDING — SOURCE ===')

function walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      walk(full)
      continue
    }
    if (!SOURCE_EXT.test(entry.name)) continue
    if (SELF.has(entry.name)) continue
    scanned += 1
    scanText(full.replace(/\\/g, '/'), fs.readFileSync(full, 'utf8'))
  }
}

for (const root of SOURCE_ROOTS) {
  if (fs.existsSync(root)) walk(root)
}

console.log(`      scanned ${scanned} source files`)

console.log('')
console.log('=== 2. FORBIDDEN WORDING — BUILT OUTPUT ===')

/**
 * The dist scan is OPTIONAL rather than fatal: `npm run build` may
 * not have run yet. But when a bundle IS present, the same phrases
 * must not appear in it — which catches a runtime-assembled string
 * that no source grep can see.
 */
const distDir = 'dist'
let distFiles = 0

if (fs.existsSync(distDir)) {
  const walkDist = (dir) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name)
      if (entry.isDirectory()) {
        walkDist(full)
        continue
      }
      if (!/\.(js|mjs|css|html)$/.test(entry.name)) continue
      distFiles += 1
      scanText(
        full.replace(/\\/g, '/'),
        fs.readFileSync(full, 'utf8'),
      )
    }
  }
  walkDist(distDir)
  console.log(`      scanned ${distFiles} built files`)
} else {
  console.log('      skip  dist/ not built yet — run `npm run build` to cover this')
}

console.log('')
console.log('=== 3. REQUIRED HONESTY STRINGS ===')

/**
 * The other direction: phrases that MUST be present.
 *
 * A test that only forbids things can be satisfied by deleting the
 * affected feature. These assertions ensure the honest wording did
 * not get "simplified" away along the way — in particular the two
 * mandatory provenance sentences, which are the only thing
 * distinguishing "no credentials found" from "content is fine".
 */
const REQUIRED = [
  {
    label: 'provenance absence sentence (English)',
    file: 'src/i18n/translations.ts',
    needle: 'No verifiable Content Credentials were found.',
  },
  {
    label: 'provenance absence disclaimer (English)',
    file: 'src/i18n/translations.ts',
    needle:
      'The absence of Content Credentials does not prove that the content is authentic or synthetic.',
  },
  {
    label: 'provenance absence sentence (Arabic)',
    file: 'src/i18n/translations.ts',
    needle: 'لم يُعثر على بيانات اعتماد محتوى قابلة للتحقق.',
  },
  {
    label: 'digital trust assessment label',
    file: 'src/i18n/translations.ts',
    needle: 'Digital Trust Assessment',
  },
  {
    label: 'detector conflict headline',
    file: 'src/i18n/translations.ts',
    needle: 'DETECTOR CONFLICT',
  },
  {
    label: 'abstention decision line',
    file: 'src/i18n/translations.ts',
    needle: 'Decision: Abstained',
  },
  {
    label: 'C2PA module is labelled Limited',
    file: 'src/i18n/translations.ts',
    needle: "moduleLabel: { en: 'C2PA module'",
  },
  {
    label: 'blind-test caveat, exact',
    file: 'src/data/blindDefenseTest.ts',
    needle:
      'This evaluation is a controlled defense set and does not represent universal real-world accuracy.',
  },
]

for (const item of REQUIRED) {
  checks += 1
  if (!fs.existsSync(item.file)) {
    failures += 1
    console.error(`FAIL  ${item.label} — ${item.file} is missing`)
    continue
  }
  const source = fs.readFileSync(item.file, 'utf8')
  if (!source.includes(item.needle)) {
    failures += 1
    console.error(`FAIL  ${item.label} — not found in ${item.file}`)
  } else {
    console.log(`ok    ${item.label}`)
  }
}

console.log('')
console.log('=== 4. NO AVERAGING OF DETECTOR PROBABILITIES ===')

/**
 * A structural check, not a copy check.
 *
 * The single most damaging thing this frontend could do is quietly
 * average two disagreeing detectors into a midpoint. The backend
 * deliberately withholds `syntheticLikelihood` on conflict, so the
 * frontend must not reconstruct it. These assertions confirm the
 * provider passes the value through untouched and that the UI never
 * reduces the detector array to a mean.
 */
const STRUCTURAL = [
  {
    label: 'evidence provider never computes a mean over detectors',
    file: 'src/features/analysis/evidenceProvider.ts',
    // Any / length or reduce over syntheticProbability would be an
    // average. Neither may appear.
    forbid: [/syntheticProbability[^;]*\/[^;]*length/, /reduce\([^)]*syntheticProbability/],
  },
  {
    // The ensemble object — and therefore syntheticLikelihood — is
    // carried through whole rather than rebuilt field by field, so
    // there is no code path that could substitute a value for it.
    label: 'evidence provider passes the whole ensemble through untouched',
    file: 'src/features/analysis/evidenceProvider.ts',
    require: [/ensemble: payload\.ensemble \?\? null/],
    forbid: [/syntheticLikelihood:\s*(?!payload)/],
  },
  {
    label: 'result view renders the conflict block',
    file: 'src/features/result/EvidenceResultView.tsx',
    require: [/data-testid="detector-conflict"/, /DetectorConflict/],
  },
  {
    label: 'result view hides the combined likelihood when null',
    file: 'src/features/result/EvidenceResultView.tsx',
    require: [/ensemble\.syntheticLikelihood !== null/],
  },
  {
    /**
     * The evidence endpoint must ALWAYS be called with mode=auto.
     *
     * Verified against the live service: an explicit mode that
     * contradicts the content makes the backend resolve to an
     * annotated string ("image (requested 'screenshot' contradicted
     * the content)"), which then fails every branch membership test
     * and returns a nine-key stub with no image analysis, no
     * provenance, no OCR and no QR. `auto` is both more correct (the
     * bytes are the authority) and immune to that annotation.
     */
    label: 'evidence requests always use mode=auto',
    file: 'src/features/analysis/evidenceProvider.ts',
    require: [/mode=\$\{modeForSignal\(\)\}/],
    forbid: [/mode=\$\{modeForSignal\([^)]*[a-z]/],
  },
]

for (const item of STRUCTURAL) {
  const source = fs.existsSync(item.file)
    ? fs.readFileSync(item.file, 'utf8')
    : ''
  if (item.forbid) {
    for (const pattern of item.forbid) {
      checks += 1
      if (pattern.test(source)) {
        failures += 1
        console.error(`FAIL  ${item.label} — matched ${pattern}`)
      } else {
        console.log(`ok    ${item.label}`)
      }
    }
  }
  if (item.require) {
    for (const pattern of item.require) {
      checks += 1
      if (!pattern.test(source)) {
        failures += 1
        console.error(`FAIL  ${item.label} — missing ${pattern}`)
      } else {
        console.log(`ok    ${item.label}`)
      }
    }
  }
}

console.log('')
console.log('=== 5. BLIND TEST FIGURES ARE TRANSCRIBED, NOT INVENTED ===')

/**
 * The blind-test figures are transcribed from
 * `backend/results/phase37/blind_defense_test.json`. If the backend
 * file is reachable, these checks confirm the frontend copy still
 * matches it — so a change to the real evaluation cannot silently
 * leave stale numbers in the UI, and, more importantly, the frontend
 * numbers cannot have drifted away from the source on their own.
 */
const SOURCE_JSON = path.join(
  '..',
  'backend',
  'results',
  'phase37',
  'blind_defense_test.json',
)

if (fs.existsSync(SOURCE_JSON)) {
  const raw = JSON.parse(fs.readFileSync(SOURCE_JSON, 'utf8'))
  const frontend = fs.readFileSync('src/data/blindDefenseTest.ts', 'utf8')

  const expected = [
    ['sample count', String(raw.overall.n)],
    ['synthetic count', String(raw.overall.n_synthetic)],
    ['real count', String(raw.overall.n_real)],
    ['false authentic count', String(raw.overall.false_authentic_count)],
    ['detector A false authentic', String(raw.per_detector_false_authentic.detector_a.false_authentic_count)],
    ['detector B false authentic', String(raw.per_detector_false_authentic.detector_b.false_authentic_count)],
    ['disagreements', String(raw.detector_disagreements)],
    ['abstention rate', String(raw.overall.abstention_rate)],
    ['out of distribution', String(raw.distribution_status_counts.out_of_distribution)],
    ['mean latency', String(raw.mean_duration_ms)],
  ]

  for (const [label, value] of expected) {
    checks += 1
    if (!frontend.includes(value)) {
      failures += 1
      console.error(
        `FAIL  blind test ${label} — frontend does not carry the backend value ${value}`,
      )
    } else {
      console.log(`ok    blind test ${label} = ${value}`)
    }
  }
} else {
  console.log(
    `skip  backend blind_defense_test.json not reachable at ${SOURCE_JSON}`,
  )
}

console.log('')
console.log(`${checks - failures}/${checks} checks passed`)
if (failures > 0) {
  console.error(`${failures} FAILED`)
  process.exit(1)
}
console.log('All wording checks passed.')