import { useI18n } from '../../i18n/useI18n'
import { cn } from '../../lib/utils'
import { ResultSection } from './resultPrimitives'
import type { EvidenceDetail } from '../../types/analysis'

/** Coverage: what actually ran vs what was skipped/unavailable/failed.
 *
 * The point of this panel is to keep "we found nothing" and "we looked
 * for nothing" never confused. Every branch in the pipeline is listed
 * with an explicit state.
 */

const COVERAGE_BRANCHES = [
  { key: 'provenance', labelKey: 'result.prov.title' },
  { key: 'ocr', labelKey: 'result.ocr' },
  { key: 'qr', labelKey: 'result.qr' },
  { key: 'urls', labelKey: 'result.urls' },
  { key: 'encoding', labelKey: 'result.encoding' },
  { key: 'file', labelKey: 'result.fileKind' },
] as const

export function EvidenceCoverage({ evidence }: { evidence: EvidenceDetail }) {
  const { t } = useI18n()

  /** Backward compatibility: older payloads had no coverage block.
   *  Each branch tests what the pipeline actually measures. */
  const hasCoverage = Boolean(evidence.coverage)

  return (
    <ResultSection
      index="06"
      title={t('result.coverage')}
      subtitle={t('result.coverageSub')}
    >
      <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {COVERAGE_BRANCHES.map((branch) => {
          const statusKey = branch.key as keyof typeof evidence.coverage
          const value = hasCoverage
            ? (evidence.coverage?.[statusKey] as string | undefined)
            : undefined

          let displayKey: string
          let tone: 'default' | 'caution' | 'trust' | 'risk' = 'default'

          if (!hasCoverage || !value) {
            displayKey = t('result.coverageNo')
          } else if (value === 'available' || value === 'analyzed') {
            displayKey = t('result.coverageAvailable')
            tone = 'trust'
          } else if (value === 'not_applicable') {
            displayKey = t('result.coverageN_A')
          } else if (value === 'unavailable') {
            displayKey = t('result.coverageUnavailable')
            tone = 'caution'
          } else {
            displayKey = t('result.coverageFailed')
            tone = 'risk'
          }

          return (
            <li
              key={branch.key}
              className="flex items-center justify-between gap-3 rounded-md border border-line/60 bg-surface-inset/40 px-3.5 py-2.5"
            >
              <span className="font-arabic-body text-[0.74rem] text-text-muted">
                {t(branch.labelKey)}
              </span>
              <span
                className={cn(
                  'font-arabic-body text-[0.68rem]',
                  tone === 'trust' ? 'text-trusted' : tone === 'caution' ? 'text-caution' : tone === 'risk' ? 'text-danger' : 'text-text-dim',
                )}
              >
                {displayKey}
              </span>
            </li>
          )
        })}
      </ul>
    </ResultSection>
  )
}

/** Missing / unavailable evidence: shown only when it materially
 *  affects interpretation. */
export function MissingEvidence({ evidence }: { evidence: EvidenceDetail }) {
  const { t } = useI18n()
  const missing: string[] = []

  if (evidence.provenance?.status === 'unavailable') {
    missing.push(t('result.missing.noProvenance'))
  }
  if (evidence.ocr === null || (evidence.ocr?.engine === 'none')) {
    missing.push(t('result.missing.ocrUnavailable'))
  }
  if (evidence.qr?.payload === null) {
    missing.push(t('result.missing.noQr'))
  }
  if (evidence.urls.length === 0) {
    missing.push(t('result.missing.noUrls'))
  }

  const hasMissing = missing.length > 0

  return (
    hasMissing && (
      <ResultSection
        index="08"
        title={t('result.missing.title')}
        subtitle={t('result.missing.subtitle')}
      >
        <ul className="space-y-3">
          {missing.map((item, index) => (
            <li
              key={index}
              className="flex items-start gap-3 rounded-md border border-caution/20 bg-caution/5 p-3.5"
            >
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-caution/20 text-[0.55rem] font-medium text-caution">
                !
              </span>
              <p className="font-arabic-body text-[0.72rem] leading-relaxed text-text">
                {item}
              </p>
            </li>
          ))}
        </ul>
      </ResultSection>
    )
  )
}
