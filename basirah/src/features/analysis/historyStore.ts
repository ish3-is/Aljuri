import type { AnalysisResult, RiskLevel } from '../../types/analysis'

/* ============================================================
   LOCAL ANALYSIS HISTORY

   The Dashboard is allowed to show something the reader produced
   themselves. It is NOT allowed to invent a figure. So the only
   numbers on that page that are not configuration counts are
   derived from this record — and this record is deliberately the
   smallest thing that supports an honest chart.

   WHAT IS STORED, and nothing else:
     · timestamp
     · modality (image / url / other)
     · three-way assessment, or null for modalities without one
     · risk band
     · trust score

   WHAT IS NEVER STORED:
     · image bytes, object URLs, or file contents
     · the submitted URL string (it can identify a private person)
     · metadata, filenames, GPS data, or any other measured detail
     · anything at all that would leave the meaning of "a summary of
       a number the model already returned"

   This is the whole reason the Dashboard can show real history
   without becoming a content database: the record is a row of
   counts, not an archive of evidence.
   ============================================================ */

export interface HistoryEntry {
  /** ISO timestamp of the completed analysis. */
  at: string
  /**
   * Four real intake modalities plus a catch-all.
   *
   * Screenshot and File are separate buckets rather than being folded
   * into Image, because the evidence pipeline branches differently
   * for each and a reader looking at this mix is asking "which kinds
   * of thing am I actually submitting?" — three different answers
   * when screenshot and file are merged into one bar.
   */
  modality: 'image' | 'screenshot' | 'file' | 'url' | 'other'
  /**
   * The pipeline's own final-assessment vocabulary, or null where
   * the modality computes no three-way classification at all.
   *
   * Note this is deliberately NOT collapsed into the old
   * likely_authentic value: "no strong synthetic indicators" is not
   * "authentic", and a history chart that showed the latter would be
   * reporting something the pipeline never said.
   */
  assessment: AssessmentKind | null
  riskLevel: RiskLevel
  trust: number
}

/** The five states the ensemble can return. */
export type AssessmentKind =
  | 'likely_synthetic'
  | 'uncertain'
  | 'no_strong_synthetic_indicators'
  | 'provenance_verified'
  | 'provenance_unavailable'

const HISTORY_KEY = 'basirah.history.v1'

/**
 * Fired on the window whenever the local record changes.
 *
 * The native `storage` event is useless here: it fires in OTHER
 * tabs, not the one that wrote the value. An analysis runs in the
 * Analyze section while the Dashboard is unmounted, so without this
 * signal the charts would show stale data until a manual refresh.
 * A same-document CustomEvent reaches the Dashboard directly.
 */
export const HISTORY_CHANGED_EVENT = 'basirah:history-changed'

/** Bounded so the local record cannot grow without limit. */
const MAX_ENTRIES = 50

const ASSESSMENT_KINDS: AssessmentKind[] = [
  'likely_synthetic',
  'uncertain',
  'no_strong_synthetic_indicators',
  'provenance_verified',
  'provenance_unavailable',
]

function isHistoryEntry(value: unknown): value is HistoryEntry {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return false
  const record = value as Record<string, unknown>
  const assessment = record.assessment
  return (
    typeof record.at === 'string' &&
    (record.modality === 'image' ||
      record.modality === 'screenshot' ||
      record.modality === 'file' ||
      record.modality === 'url' ||
      record.modality === 'other') &&
    (assessment === null || ASSESSMENT_KINDS.includes(assessment as AssessmentKind)) &&
    (record.riskLevel === 'trusted' ||
      record.riskLevel === 'caution' ||
      record.riskLevel === 'high_risk') &&
    typeof record.trust === 'number'
  )
}

export function loadHistory(): HistoryEntry[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = window.localStorage.getItem(HISTORY_KEY)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    // Oldest first — the charts plot a time series.
    return parsed.filter(isHistoryEntry).sort((a, b) => a.at.localeCompare(b.at))
  } catch {
    return []
  }
}

/**
 * Project a completed analysis into the minimal record and persist it.
 *
 * Only called on a REAL completed analysis, never on a mock, so the
 * Dashboard's history can never be inflated by demo traffic.
 */
export function recordAnalysis(result: AnalysisResult): HistoryEntry[] {
  if (result.isMock) return loadHistory()

  const detail = result.imageDetail
  const modality: HistoryEntry['modality'] =
    result.signal.kind === 'url' || result.signal.kind === 'text'
      ? 'url'
      : result.signal.kind === 'screenshot'
        ? 'screenshot'
        : result.signal.kind === 'file'
          ? 'file'
          : result.signal.kind === 'image' || result.signal.kind === 'qr'
            ? 'image'
            : 'other'

  // An evidence result carries its own final assessment, which is
  // richer than the legacy three-way image classification. It is
  // recorded AS RETURNED — no widening, no narrowing.
  const evidence = (result as { evidence?: { fusion?: { finalAssessment?: string } } })
    .evidence
  const evidenceAssessment = evidence?.fusion?.finalAssessment

  const entry: HistoryEntry = {
    at: new Date().toISOString(),
    modality,
    // The legacy image pipeline still reports its own three-way
    // value, including `likely_authentic` — which the evidence
    // vocabulary deliberately does not contain, because that pipeline
    // predates the distinction between "no indicators found" and
    // "authentic". It is recorded verbatim rather than remapped: the
    // chart shows only rows that have counts, and inventing a mapping
    // here would attribute the ensemble's words to the older model.
    assessment: evidenceAssessment
      ? (evidenceAssessment as AssessmentKind)
      : ((detail?.assessment ?? null) as AssessmentKind | null),
    riskLevel: result.riskLevel,
    trust: result.trustScore,
  }

  const next = [...loadHistory(), entry].slice(-MAX_ENTRIES)
  try {
    window.localStorage.setItem(HISTORY_KEY, JSON.stringify(next))
  } catch {
    // Storage denied: the record simply is not kept. Charts fall back
    // to the empty state, which is the honest outcome.
  }
  announceChange()
  return next
}

function announceChange(): void {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new CustomEvent(HISTORY_CHANGED_EVENT))
}

export function clearHistory(): void {
  try {
    window.localStorage.removeItem(HISTORY_KEY)
  } catch {
    // Nothing to do; the record is already unreadable.
  }
  announceChange()
}

/** Count by a derived key, for the categorical charts. */
export function countBy<T extends string>(
  entries: HistoryEntry[],
  key: (entry: HistoryEntry) => T,
): Record<T, number> {
  const counts = {} as Record<T, number>
  for (const entry of entries) {
    const bucket = key(entry)
    counts[bucket] = (counts[bucket] ?? 0) + 1
  }
  return counts
}