import { useCallback, useState } from 'react'
import { motion } from 'motion/react'
import { ArrowLeft, FileText, Trash2 } from 'lucide-react'
import { Panel, SectionLabel } from '../components/ui/primitives'
import { ReportDocumentView } from '../features/reports/ReportDocumentView'
import { ReportExports } from '../features/reports/ReportExports'
import { deleteReport, loadReports } from '../features/reports/reportStore'
import type { ReportDocument } from '../types/report'
import { useI18n } from '../i18n/useI18n'
import type { TranslationKey } from '../i18n/translations'

/* ============================================================
   REPORTS CENTER

   Two views in one section, switched by local state rather than a
   second route: the hash router already carries the section, and a
   report id in the URL would imply the report is addressable from
   outside this device — which it is not, since nothing is uploaded.

   The list is an honest local archive. When it is empty the section
   says so and points at the Analyze section rather than filling the
   space with a sample report, because a sample report would look
   exactly like a real one.
   ============================================================ */

const MODALITY_LABEL_KEYS = {
  image: 'reports.modalities.image',
  screenshot: 'reports.modalities.screenshot',
  qr: 'reports.modalities.qr',
  url: 'reports.modalities.url',
  text: 'reports.modalities.text',
  file: 'reports.modalities.file',
} as const satisfies Record<ReportDocument['modality'], TranslationKey>

const RISK_TEXT = {
  trusted: 'score.trusted',
  caution: 'score.caution',
  high_risk: 'score.highRisk',
} as const satisfies Record<ReportDocument['riskLevel'], TranslationKey>

/* ------------------------------------------------------------------ */
/* Empty state                                                          */
/* ------------------------------------------------------------------ */

function EmptyState() {
  const { t } = useI18n()

  return (
    <Panel className="flex flex-col items-center px-6 py-16 text-center">
      <span aria-hidden className="text-text-dim">
        <FileText size={26} />
      </span>
      <p className="font-arabic-body mt-4 text-[0.95rem] text-text">
        {t('reports.empty')}
      </p>
      <p className="font-arabic-body mt-2 max-w-md text-[0.78rem] leading-relaxed text-text-dim">
        {t('reports.emptyHint')}
      </p>
    </Panel>
  )
}

/* ------------------------------------------------------------------ */
/* List                                                                 */
/* ------------------------------------------------------------------ */

function ReportList({
  reports,
  onOpen,
  onDelete,
}: {
  reports: ReportDocument[]
  onOpen: (report: ReportDocument) => void
  onDelete: (reportId: string) => void
}) {
  const { t } = useI18n()

  return (
    <Panel className="divide-y divide-line/50">
      {reports.map((report, index) => (
        <motion.div
          key={report.reportId}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: Math.min(index * 0.04, 0.3), duration: 0.4 }}
          className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3 px-5 py-4"
        >
          <button
            type="button"
            onClick={() => onOpen(report)}
            className="min-w-0 flex-1 text-start"
          >
            <p dir="ltr" className="ltr-embed text-[0.8rem] text-signal">
              {report.reportId}
            </p>
            {/* The analysed item is Latin in both languages (a
                filename or a URL), so it stays LTR in Arabic. */}
            <p
              dir="ltr"
              className="ltr-embed mt-1 truncate text-[0.74rem] text-text-muted"
            >
              {report.inputSummary}
            </p>
            <p className="font-arabic-body mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[0.68rem] text-text-dim">
              <span>{t(MODALITY_LABEL_KEYS[report.modality])}</span>
              <span aria-hidden>·</span>
              <span>
                {t('charts.labelRisk')}: {t(RISK_TEXT[report.riskLevel])}
              </span>
              <span aria-hidden>·</span>
              <span>
                {t('charts.labelTrust')}:{' '}
                <span dir="ltr" className="ltr-embed">
                  {String(Math.round(report.trust)).padStart(2, '0')}
                </span>
              </span>
            </p>
          </button>

          <div className="flex shrink-0 items-center gap-2">
            <button
              type="button"
              onClick={() => onOpen(report)}
              className="rounded-full border border-line px-3.5 py-1.5 text-[0.72rem] text-text-muted transition-colors hover:border-line-bright hover:text-text"
            >
              {t('reports.open')}
            </button>
            <button
              type="button"
              onClick={() => onDelete(report.reportId)}
              aria-label={`${t('reports.delete')}: ${report.reportId}`}
              className="inline-flex size-8 items-center justify-center rounded-full border border-line text-text-dim transition-colors hover:border-danger/50 hover:text-danger"
            >
              <Trash2 size={13} />
            </button>
          </div>
        </motion.div>
      ))}
    </Panel>
  )
}

/* ------------------------------------------------------------------ */
/* Section                                                              */
/* ------------------------------------------------------------------ */

export function ReportsPage() {
  const { t } = useI18n()
  const [reports, setReports] = useState<ReportDocument[]>(() => loadReports())
  const [open, setOpen] = useState<ReportDocument | null>(null)

  const handleDelete = useCallback((reportId: string) => {
    // A destructive action on a document the reader may care about
    // asks first. There is no undo and nothing is stored elsewhere.
    if (!window.confirm(t('reports.deleteConfirm'))) return
    setReports(deleteReport(reportId))
    setOpen((current) => (current?.reportId === reportId ? null : current))
  }, [t])

  const handleOpen = useCallback(
    (report: ReportDocument) => setOpen(report),
    [],
  )

  const handleBack = useCallback(() => setOpen(null), [])

  // ---- single report view ----
  if (open) {
    return (
      <div className="px-5 pt-28 pb-10 sm:px-8 sm:pt-32">
        <div className="mx-auto max-w-[1000px]">
          <button
            type="button"
            onClick={handleBack}
            className="inline-flex items-center gap-2 rounded-full border border-line px-4 py-2 text-[0.78rem] text-text-muted transition-colors hover:border-line-bright hover:text-text"
          >
            <ArrowLeft size={13} className="rtl:-scale-x-100" />
            {t('reports.back')}
          </button>

          <div className="mt-6">
            <ReportExports report={open} />
          </div>

          <div className="mt-6 rounded-lg border border-line/70 bg-surface/45">
            <ReportDocumentView report={open} />
          </div>
        </div>
      </div>
    )
  }

  // ---- list view ----
  return (
    <div className="px-5 pt-28 pb-10 sm:px-8 sm:pt-32">
      <div className="mx-auto max-w-[1400px]">
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        >
          <SectionLabel
            index="01"
            title={t('reports.title')}
            subtitle={t('reports.subtitle')}
          />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.6 }}
          className="max-w-4xl"
        >
          {reports.length === 0 ? (
            <EmptyState />
          ) : (
            <ReportList
              reports={reports}
              onOpen={handleOpen}
              onDelete={handleDelete}
            />
          )}
        </motion.div>
      </div>
    </div>
  )
}