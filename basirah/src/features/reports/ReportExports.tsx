import { useState } from 'react'
import { FileSpreadsheet, Printer, FileDown } from 'lucide-react'
import { useI18n } from '../../i18n/useI18n'
import { exportReportToExcel } from './exportExcel'
import type { ReportDocument } from '../../types/report'

/* ============================================================
   REPORT EXPORT CONTROLS

   Three exports, one report:

     PRINT  window.print() against the print stylesheet. This is the
            correct PDF path: the browser's own paginator produces a
            real vector PDF with selectable text, correct page
            breaks and embedded fonts. Generating a PDF client-side
            with a canvas or an html-to-canvas rasteriser would give
            a screenshot of the page — exactly what a report must
            not be.

     PDF    the same call. The browser print dialogue is where the
            destination becomes "Save as PDF". Labelling it
            separately is honest: it is the reader's choice of
            destination, not a second code path.

     EXCEL  a structured workbook, built with a dynamic import so
            the library never enters the initial bundle.
   ============================================================ */

interface ReportExportsProps {
  report: ReportDocument
}

export function ReportExports({ report }: ReportExportsProps) {
  const { t } = useI18n()
  const [busy, setBusy] = useState<'print' | 'excel' | null>(null)
  const [error, setError] = useState(false)

  const handlePrint = () => {
    setBusy('print')
    // A short delay lets the button's pressed state paint before the
    // modal print dialogue blocks the main thread, so the reader
    // sees feedback rather than a frozen page.
    window.setTimeout(() => {
      window.print()
      setBusy(null)
    }, 120)
  }

  const handleExcel = async () => {
    setBusy('excel')
    setError(false)
    try {
      await exportReportToExcel(report)
    } catch {
      // A failed export must say so. Silently doing nothing would
      // read as "the file is being prepared".
      setError(true)
    } finally {
      setBusy(null)
    }
  }

  const buttonClass =
    'inline-flex items-center gap-2 rounded-full border border-line bg-surface-raised/60 px-4 py-2 text-[0.76rem] text-text-muted transition-colors duration-200 hover:border-line-bright hover:text-text disabled:pointer-events-none disabled:opacity-45'

  return (
    <div className="basirah-print-hide">
      <div
        role="group"
        aria-label={t('exportSection.printControlsLabel')}
        className="flex flex-wrap items-center gap-2"
      >
        <button type="button" onClick={handlePrint} disabled={busy !== null} className={buttonClass}>
          <Printer size={14} />
          {busy === 'print' ? t('exportSection.printPreparing') : t('exportSection.print')}
        </button>

        <button type="button" onClick={handlePrint} disabled={busy !== null} className={buttonClass}>
          <FileDown size={14} />
          {t('export.pdf')}
        </button>

        <button
          type="button"
          onClick={() => void handleExcel()}
          disabled={busy !== null}
          className={buttonClass}
        >
          <FileSpreadsheet size={14} />
          {busy === 'excel' ? t('export.excelPreparing') : t('export.excel')}
        </button>
      </div>

      <p className="font-arabic-body mt-2 max-w-xl text-[0.68rem] leading-relaxed text-text-dim">
        {t('export.pdfHint')}
      </p>

      {error && (
        <p role="alert" className="mt-2 text-[0.7rem] text-danger">
          {t('export.failed')}
        </p>
      )}
    </div>
  )
}