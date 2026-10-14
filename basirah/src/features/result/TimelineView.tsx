import { useI18n } from '../../i18n/useI18n'
import { cn } from '../../lib/utils'
import type { TimelineStageId } from '../../types/analysis'

/* ============================================================
   INVESTIGATION TIMELINE 2.0
   ============================================================
   Strict separation:
   - BASIRAH ANALYSIS TIMELINE — the analysis stages
   - CONTENT HISTORY — only C2PA/provenance history if present
   Never mixed.
   ============================================================ */

interface TimelineEntry {
  id: TimelineStageId
  labelEn: string
  labelAr: string
  /** When this stage was reached (Unix ms). null = not yet reached. */
  completedAt: number | null
  /** What the stage established. */
  detailEn: string
  detailAr: string
  /** True when this stage ran successfully. */
  ran: boolean
  /** When present, this is a CONTENT HISTORY stage, not BASIRAH analysis. */
  contentHistory?: boolean
}

interface TimelineViewProps {
  entries: TimelineEntry[]
  /** Show the content-history section separately only when real C2PA history exists. */
  showContentHistory?: boolean
}

const STAGE_ORDER: TimelineStageId[] = [
  'acquire',
  'identify',
  'visual',
  'metadata',
  'provenance',
  'synthetic',
  'correlate',
  'score',
]

/** Deterministic stage order: BASIRAH analysis stages first, content history after. */
function sortedEntries(entries: TimelineEntry[]): TimelineEntry[] {
  const analysis = entries.filter(e => !e.contentHistory)
  const contentHistory = entries.filter(e => e.contentHistory)
  return [...analysis.sort((a, b) => {
    const ai = STAGE_ORDER.indexOf(a.id)
    const bi = STAGE_ORDER.indexOf(b.id)
    if (ai === -1 && bi === -1) return 0
    if (ai === -1) return 1
    if (bi === -1) return -1
    return ai - bi
  }), ...contentHistory]
}

/** Build the timeline from the evidence API response's `timeline` events. */
// eslint-disable-next-line react-refresh/only-export-components
export function buildTimelineEntries(events: Array<{ stage: string; status: string; detail: string }>): TimelineEntry[] {
  const stageLabels: Record<string, { en: string; ar: string }> = {
    acquire: { en: 'Signal acquired', ar: 'تم التقاط الإشارة' },
    identify: { en: 'Content type identified', ar: 'تم التعرف على نوع المحتوى' },
    visual: { en: 'Visual structure extracted', ar: 'تم استخراج البنية البصرية' },
    url: { en: 'URL structure inspected', ar: 'تم فحص بنية الرابط' },
    metadata: { en: 'Metadata examined', ar: 'تم فحص البيانات الوصفية' },
    provenance: { en: 'Provenance checked', ar: 'تم التحقق من المصدر' },
    synthetic: { en: 'Synthetic indicators evaluated', ar: 'تم تقييم مؤشرات التوليد' },
    correlate: { en: 'Evidence correlated', ar: 'تم ربط الأدلة' },
    score: { en: 'Trust score computed', ar: 'تم احتساب درجة الثقة' },
  }

  const entries: TimelineEntry[] = []
  let lastCompleted = -1

  for (const ev of events) {
    const label = stageLabels[ev.stage] ?? { en: ev.stage, ar: ev.stage }
    const completed = ev.status === 'ok'
    if (completed) lastCompleted = Date.now()

    entries.push({
      id: ev.stage as TimelineStageId,
      labelEn: label.en,
      labelAr: label.ar,
      completedAt: completed ? lastCompleted : null,
      detailEn: ev.detail,
      detailAr: ev.detail,
      ran: completed,
    })
  }

  return sortedEntries(entries)
}

export function TimelineView({ entries, showContentHistory = false }: TimelineViewProps) {
  const { t } = useI18n()

  const filtered = showContentHistory
    ? entries
    : entries.filter(e => !e.contentHistory)

  if (filtered.length === 0) {
    return (
      <div className="rounded-lg border border-line/70 bg-surface/40 p-5">
        <h2 className="text-sm tracking-tight text-text">{t('timeline.title')}</h2>
        <p className="mt-2 text-[0.76rem] leading-relaxed text-text-dim">
          {t('timeline.emptyState')}
        </p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-line/70 bg-surface/40 p-5">
      <h2 className="text-sm tracking-tight text-text">{t('timeline.title')}</h2>
      <ol className="mt-4 space-y-0">
        {filtered.map((entry) => {
          const isLast = entry === filtered[filtered.length - 1]
          return (
            <li key={entry.id} className="flex items-start gap-3">
              <span
                className={cn(
                  'mt-1.5 flex h-2.5 w-2.5 shrink-0 rounded-full',
                  entry.ran
                    ? 'bg-signal'
                    : 'bg-line',
                )}
              />
              <div className="min-w-0 flex-1">
                <p className="font-mono text-[0.68rem] text-text-dim">
                  {entry.completedAt ? new Date(entry.completedAt).toLocaleString() : '—'}
                </p>
                <p className="text-sm font-semibold text-text">{entry.labelEn}</p>
                <p className="text-[0.68rem] leading-relaxed text-text-dim">{entry.detailEn}</p>
              </div>
              {!isLast && <span aria-hidden className="text-text-dim/40">›</span>}
            </li>
          )
        })}
      </ol>
      {showContentHistory && filtered.some(e => e.contentHistory) && (
        <div className="mt-5 border-t border-line/40 pt-4">
          <p className="mono-label text-[0.68rem] text-text-dim">{t('timeline.contentHistory')}</p>
          <ol className="mt-2 space-y-0">
            {filtered.filter(e => e.contentHistory).map((entry) => {
              const isLast = entry === filtered.filter(e => e.contentHistory)[filtered.filter(e => e.contentHistory).length - 1]
              return (
                <li key={entry.id} className="flex items-start gap-3">
                  <span
                    className={cn(
                      'mt-1.5 flex h-2.5 w-2.5 shrink-0 rounded-full',
                      entry.ran ? 'bg-signal' : 'bg-line',
                    )}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="text-[0.68rem] text-text-dim">{entry.completedAt ? new Date(entry.completedAt).toLocaleString() : '—'}</p>
                    <p className="text-sm font-semibold text-text">{entry.labelEn}</p>
                    <p className="text-[0.68rem] leading-relaxed text-text-dim">{entry.detailEn}</p>
                  </div>
                  {!isLast && <span aria-hidden className="text-text-dim/40">›</span>}
                </li>
              )
            })}
          </ol>
        </div>
      )}
    </div>
  )
}
