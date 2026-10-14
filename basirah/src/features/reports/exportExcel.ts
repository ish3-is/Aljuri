import type { ReportDocument } from '../../types/report'

/* ============================================================
   EXCEL EXPORT

   A real .xlsx with one sheet per evidence category — never a JSON
   blob in a single cell, which is what "export to Excel" usually
   degrades into and which makes the file useless for analysis.

   SECURITY — FORMULA INJECTION. This is the critical control.

   A report contains strings the reader supplied: the analysed URL,
   the filename, evidence labels, model limitation prose. Excel
   treats a cell whose text begins with `=`, `+`, `-` or `@` as a
   FORMULA and evaluates it. A URL such as
   `=HYPERLINK("http://evil","click")` or a filename beginning with
   `-` would therefore execute on open, in the reader's spreadsheet,
   with their permissions.

   The fix is `sanitizeCell`: if a string's first meaningful
   character is one of those four, prefix it with an apostrophe.
   In Excel that apostrophe is the "treat as text" marker — it is not
   displayed, and the cell reads back as the literal string. Applied
   to EVERY user-controlled and model-derived string on every sheet,
   before it reaches the workbook.

   ExcelJS is loaded with a dynamic import so it never enters the
   initial bundle.
   ============================================================ */

/** Leading characters Excel interprets as the start of a formula. */
const FORMULA_TRIGGERS = ['=', '+', '-', '@']

/**
 * Neutralise spreadsheet formula injection.
 *
 * Prefixing with `'` is the standard, tool-agnostic defence: Excel,
 * LibreOffice and Numbers all honour it as a text marker.
 *
 * The check skips leading whitespace and control characters first,
 * because Excel itself ignores them when deciding whether a cell is
 * a formula — a string of `" =cmd()"` would otherwise slip past a
 * naive `startsWith('=')` test.
 */
export function sanitizeCell(value: string): string {
  // Find the first character Excel would actually look at.
  let index = 0
  while (
    index < value.length &&
    (value[index] === ' ' ||
      value[index] === '\t' ||
      value[index] === '\n' ||
      value[index] === '\r' ||
      value[index] === '\v' ||
      value[index] === '\f')
  ) {
    index += 1
  }

  const first = value[index]
  if (first !== undefined && FORMULA_TRIGGERS.includes(first)) {
    return `'${value}`
  }
  return value
}

/** Sanitise a number-ish string without turning a measurement into text. */
function safeNumber(value: number | null): number | string {
  return value === null ? '' : value
}

/** A sheet is a title, a column header row, and rows of cells. */
interface SheetSpec {
  name: string
  columns: Array<{ header: string; key: string; width: number }>
  rows: Array<Record<string, string | number>>
}

/** Build the sheet set for a report. Pure data — no workbook here. */
function buildSheets(report: ReportDocument): SheetSpec[] {
  const sheets: SheetSpec[] = []

  sheets.push({
    name: 'Summary',
    columns: [
      { header: 'Field', key: 'field', width: 30 },
      { header: 'Value', key: 'value', width: 78 },
    ],
    rows: [
      { field: 'Report ID', value: report.reportId },
      { field: 'Generated (ISO 8601)', value: report.createdAt },
      { field: 'Modality', value: report.modality },
      { field: 'Analysed item', value: report.inputSummary },
      {
        field: 'Assessment',
        value: report.assessment ?? 'Not applicable to this modality',
      },
      { field: 'Trust score (0-100)', value: report.trust },
      {
        field: 'Model confidence (0-100)',
        // 'not measured' rather than 0, for the same reason the
        // document does it: an unmeasured value is not a zero.
        value: report.confidence ?? 'not measured',
      },
      { field: 'Risk band', value: report.riskLevel },
      { field: 'Executive summary', value: report.overallAssessment },
      { field: 'Safety disclaimer', value: report.safety },
    ],
  })

  sheets.push({
    name: 'Evidence',
    columns: [
      { header: 'ID', key: 'id', width: 22 },
      { header: 'Finding', key: 'label', width: 40 },
      { header: 'Detail', key: 'detail', width: 72 },
      { header: 'Polarity', key: 'polarity', width: 14 },
      { header: 'Weight', key: 'weight', width: 14 },
    ],
    rows: report.evidence.map((item) => ({
      id: item.id,
      label: item.label,
      detail: item.detail,
      polarity: item.polarity,
      weight: item.weight,
    })),
  })

  sheets.push({
    name: 'Timeline',
    columns: [
      { header: 'Order', key: 'order', width: 10 },
      { header: 'Stage', key: 'stage', width: 28 },
      { header: 'Offset (s)', key: 'offset', width: 14 },
    ],
    rows: report.timeline.map((item, index) => ({
      order: index + 1,
      stage: item.stage,
      offset: item.offsetSeconds,
    })),
  })

  sheets.push({
    name: 'Metadata',
    columns: [
      { header: 'Field', key: 'field', width: 30 },
      { header: 'Value', key: 'value', width: 52 },
    ],
    rows: report.metadata.map((row) => ({ field: row.labelKey, value: row.valueEn })),
  })

  sheets.push({
    name: 'Model Info',
    columns: [
      { header: 'Field', key: 'field', width: 30 },
      { header: 'Value', key: 'value', width: 78 },
    ],
    rows: [
      { field: 'Engine', value: report.modelInfo.engine },
      { field: 'Engine version', value: report.modelInfo.engineVersion },
      { field: 'Status', value: report.modelInfo.statusEn },
      { field: 'Advisory only', value: String(report.modelInfo.advisoryOnly) },
      {
        field: 'Fit for automated enforcement',
        value: String(report.modelInfo.fitForAutomatedEnforcement),
      },
      ...report.modelInfo.limitationsEn.map((limitation, index) => ({
        field: `Limitation ${index + 1}`,
        value: limitation,
      })),
    ],
  })

  // Image-only sheets. Omitted entirely when the modality produced no
  // such data — an empty sheet would imply "measured, found nothing",
  // which is not the same claim as "not measured".
  if (report.forensics.length > 0) {
    sheets.push({
      name: 'Forensics',
      columns: [
        { header: 'Characteristic', key: 'name', width: 30 },
        { header: 'Value', key: 'value', width: 14 },
        { header: 'What this indicates', key: 'meaning', width: 56 },
        { header: 'What this does not mean', key: 'notMean', width: 56 },
      ],
      rows: report.forensics.map((row) => ({
        name: row.name,
        value: safeNumber(row.value),
        meaning: row.meaningEn,
        notMean: row.doesNotMeanEn,
      })),
    })
  }

  if (report.provenance.length > 0) {
    sheets.push({
      name: 'Provenance',
      columns: [
        { header: 'Status', key: 'status', width: 24 },
        { header: 'Limitation', key: 'limitation', width: 86 },
      ],
      rows: report.provenance.map((row) => ({
        status: row.statusEn,
        limitation: row.limitationEn,
      })),
    })
  }

  if (report.urlSignals.length > 0) {
    sheets.push({
      name: 'URL Signals',
      columns: [
        { header: 'Signal', key: 'signal', width: 30 },
        { header: 'Value', key: 'value', width: 72 },
        { header: 'Severity', key: 'severity', width: 16 },
      ],
      rows: report.urlSignals.map((row) => ({
        signal: row.labelKey,
        value: row.valueEn,
        severity: row.severity,
      })),
    })
  }

  sheets.push({
    name: 'Trust DNA',
    columns: [
      { header: 'Axis', key: 'axis', width: 22 },
      { header: 'Value (0-100)', key: 'value', width: 16 },
    ],
    rows: report.dna.map((row) => ({
      axis: row.labelKey,
      value: safeNumber(row.value),
    })),
  })

  sheets.push({
    name: 'Team',
    columns: [
      { header: 'Name', key: 'name', width: 34 },
      { header: 'Student ID', key: 'id', width: 16 },
      { header: 'Specialization', key: 'specialization', width: 26 },
      { header: 'Role', key: 'role', width: 14 },
    ],
    rows: report.team.map((member) => ({
      name: member.name,
      id: member.studentId,
      specialization: member.specialization,
      role: member.isLeader ? 'Leader' : 'Team member',
    })),
  })

  return sheets
}

export async function exportReportToExcel(report: ReportDocument): Promise<void> {
  // Dynamic import: the workbook writer is the heaviest export
  // dependency and has no business in the initial bundle.
  const { default: ExcelJS } = await import('exceljs')

  const workbook = new ExcelJS.Workbook()
  workbook.creator = 'BASIRAH — Digital Trust Intelligence'
  workbook.created = new Date(report.createdAt)

  for (const spec of buildSheets(report)) {
    const sheet = workbook.addWorksheet(spec.name, {
      views: [{ state: 'frozen', ySplit: 1 }],
    })

    // Header row: bold, filled, and frozen so it stays visible while
    // a reader scrolls a long evidence list.
    const header = sheet.addRow(spec.columns.map((column) => column.header))
    header.font = { bold: true, color: { argb: 'FF0B1220' } }
    header.fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: 'FFDDE4EE' },
    }
    header.alignment = { vertical: 'middle' }
    header.height = 20

    for (const row of spec.rows) {
      // Every cell goes through sanitizeCell. Numbers pass through
      // untouched so Excel can still sum and chart them; strings are
      // neutralised against formula injection.
      sheet.addRow(
        spec.columns.map((column) => {
          const value = row[column.key]
          return typeof value === 'number' ? value : sanitizeCell(String(value))
        }),
      )
    }

    // Wrap the wide prose columns and set per-column widths.
    spec.columns.forEach((column, index) => {
      sheet.getColumn(index + 1).width = column.width
      if (column.width > 30) {
        sheet.getColumn(index + 1).alignment = { wrapText: true, vertical: 'top' }
      }
    })

    sheet.autoFilter = {
      from: { row: 1, column: 1 },
      to: { row: 1, column: spec.columns.length },
    }
  }

  const buffer = await workbook.xlsx.writeBuffer()
  const blob = new Blob([buffer], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  })

  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `${report.reportId}.xlsx`
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  URL.revokeObjectURL(url)
}