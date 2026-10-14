import type { ReportDocument } from '../../types/report'

/* ============================================================
   LOCAL REPORT STORE

   Reports live in this browser's localStorage and nowhere else.

   There is deliberately no upload path and no sync. A report can
   contain a submitted URL and a set of measured characteristics
   about someone's content; none of that belongs on a server that
   never asked to hold it. Losing the local record on cache clear is
   the correct trade for this product, and the UI says so.

   Reads are defensive: a stored report is untrusted input (it may
   have been hand-edited, or written by an older build with a
   different shape), so every field is validated on the way out
   rather than trusted.
   ============================================================ */

const REPORTS_KEY = 'basirah.reports.v1'

/** Cap the stored set. A device-local history of 40 is plenty for a
    research tool and bounds localStorage growth. */
const MAX_REPORTS = 40

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

/**
 * Structural validation of a stored report.
 *
 * Deliberately strict on identity fields and permissive on nested
 * arrays: a corrupted evidence list should degrade to "no evidence"
 * rather than discard a whole report the reader may need.
 */
function isReportDocument(value: unknown): value is ReportDocument {
  if (!isRecord(value)) return false
  return (
    typeof value.reportId === 'string' &&
    typeof value.createdAt === 'string' &&
    typeof value.inputSummary === 'string' &&
    typeof value.overallAssessment === 'string' &&
    typeof value.trust === 'number' &&
    // null is valid: it means the pipeline published no confidence
    // figure, which is different from a confidence of 0.
    (value.confidence === null || typeof value.confidence === 'number') &&
    (value.riskLevel === 'trusted' ||
      value.riskLevel === 'caution' ||
      value.riskLevel === 'high_risk') &&
    Array.isArray(value.dna) &&
    Array.isArray(value.evidence) &&
    Array.isArray(value.timeline) &&
    Array.isArray(value.team)
  )
}

export function loadReports(): ReportDocument[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = window.localStorage.getItem(REPORTS_KEY)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    // Newest first: the Reports Center lists most recent at the top.
    return parsed.filter(isReportDocument)
  } catch {
    // Corrupt JSON or denied storage. An empty list is honest.
    return []
  }
}

function persist(reports: ReportDocument[]): boolean {
  try {
    window.localStorage.setItem(REPORTS_KEY, JSON.stringify(reports))
    return true
  } catch {
    // Quota exceeded or storage denied. The in-memory report is still
    // rendered; only persistence is lost.
    return false
  }
}

/** Save a report, newest first, de-duplicating on reportId. */
export function saveReport(report: ReportDocument): ReportDocument[] {
  const existing = loadReports().filter((item) => item.reportId !== report.reportId)
  const next = [report, ...existing].slice(0, MAX_REPORTS)
  persist(next)
  return next
}

export function deleteReport(reportId: string): ReportDocument[] {
  const next = loadReports().filter((item) => item.reportId !== reportId)
  persist(next)
  return next
}

export function findReport(reportId: string): ReportDocument | null {
  return loadReports().find((item) => item.reportId === reportId) ?? null
}

/** True when at least one report exists — drives the empty state. */
export function hasReports(): boolean {
  return loadReports().length > 0
}