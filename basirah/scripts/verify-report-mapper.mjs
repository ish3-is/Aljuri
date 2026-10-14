import fs from 'node:fs'
import path from 'node:path'
import os from 'node:os'
import { rolldown } from 'rolldown'

const PAYLOAD = process.argv[2]
const OUT_DIR = path.join(os.tmpdir(), 'basirah_qa', 'mapper')
fs.mkdirSync(OUT_DIR, { recursive: true })

const entry = path.join(OUT_DIR, 'entry.ts')
fs.writeFileSync(
  entry,
  [
    `export { toEvidenceAnalysisResult } from ${JSON.stringify(path.resolve('src/features/analysis/evidenceProvider.ts'))}`,
    `export { buildEvidenceClaims, fusionExplanation, reportLimitations } from ${JSON.stringify(path.resolve('src/features/reports/evidenceReportMapper.ts'))}`,
  ].join('\n'),
  'utf8',
)

const outfile = path.join(OUT_DIR, 'bundle.mjs')
// The bundle is post-processed rather than built with `define`,
// because import.meta.env is only valid in an ESM output where the
// property does not already exist. Shimming it AFTER bundling is the
// one approach that works across bundlers, and it keeps this script
// honest: the replacement is visible in this file rather than hidden
// behind a bundler option name.
const bundle = await rolldown({ input: entry, platform: 'node' })
await bundle.write({ file: outfile, format: 'esm' })
await bundle.close()

fs.writeFileSync(
  outfile,
  fs
    .readFileSync(outfile, 'utf8')
    // DEV: true makes resolveApiBase() return the same-origin empty
    // string the browser uses in development, so no absolute URL is
    // ever constructed on this path.
    .replace(/import\.meta\.env/g, '({ DEV: true })'),
  'utf8',
)

const mod = await import(`file://${outfile.replace(/\\/g, '/')}`)
const { toEvidenceAnalysisResult, buildEvidenceClaims, fusionExplanation, reportLimitations } = mod

const payload = JSON.parse(fs.readFileSync(PAYLOAD, 'utf8'))
const result = toEvidenceAnalysisResult(payload)
const claims = buildEvidenceClaims(result)
const byKind = {}
for (const c of claims) byKind[c.kind] = (byKind[c.kind] ?? 0) + 1

console.log('mode:', payload.mode)
console.log('claims:', claims.length, JSON.stringify(byKind))
console.log('fusion:', fusionExplanation(result).en.slice(0, 80))
console.log('limitations:', reportLimitations(result).en.length)
console.log('')
for (const c of claims) console.log(`  [${c.kind}] ${c.source} :: ${c.detailEn.slice(0, 150)}`)

let bad = 0
const must = (cond, msg) => { if (!cond) { console.error('  FAIL', msg); bad++ } }

console.log('')
must(claims.length > 0, 'no claims emitted at all')
must(claims.some((c) => c.kind === 'verifiedFact'), 'no verifiedFact emitted')
if (payload.provenance) must(claims.some((c) => c.source === 'c2pa'), 'provenance produced no claims')
if (payload.provenance?.status === 'unavailable') {
  must(claims.some((c) => c.kind === 'verifiedFact' && c.detailEn.includes('No valid C2PA manifest was found.')), 'missing verified-fact C2PA absence line')
  must(claims.some((c) => c.kind === 'unavailableEvidence' && c.detailEn.includes('Publicly trusted provenance could not be established.')), 'missing unavailable-evidence provenance line')
}
if (payload.ensemble?.detectors?.length) {
  must(claims.filter((c) => c.kind === 'modelInference').length >= payload.ensemble.detectors.length, 'not every detector produced its own modelInference')
}
if (payload.ensemble?.detectorAgreement === 'conflict') {
  must(!claims.some((c) => c.detailEn.includes('combined synthetic likelihood')), 'combined likelihood claimed on conflict')
  must(claims.some((c) => c.kind === 'unavailableEvidence' && c.detailEn.includes('opposite conclusions')), 'missing conflict unavailable-evidence line')
}
if (payload.file && payload.file.accepted === false) {
  must(!claims.some((c) => c.source === 'file_intelligence' && c.kind !== 'unavailableEvidence'), 'refused file produced a non-unavailable claim')
}
if (bad > 0) { console.error(`\n${bad} FAILED`); process.exit(1) }
console.log('\nAll mapper checks passed.')
