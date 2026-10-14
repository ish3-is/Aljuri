import { useI18n } from '../../i18n/useI18n'
import { cn } from '../../lib/utils'
import { ResultSection } from './resultPrimitives'
import type { EvidenceDetail } from '../../types/analysis'

/** Separated evidence taxonomy: what was observed, what the models inferred,
* and what could not be established. */
export function FactsInferencesUncertainties({ evidence }: { evidence: EvidenceDetail }) {
  const { t } = useI18n()

  const hasFindings = Boolean(
    evidence.fusion?.findings &&
    evidence.fusion.findings.length > 0
  )

  const ensemble = evidence.ensemble
  const hasInferences = Boolean(
    ensemble !== null &&
    (ensemble.detectorAgreement === 'strong_agreement' ||
     ensemble.detectorAgreement === 'moderate_agreement' ||
     ensemble.detectorAgreement === 'insufficient' ||
     ensemble.detectorAgreement === 'conflict')
  )

  const ensembleNotes = ensemble?.notes ?? []
  const hasUncertainties = Boolean(
    (evidence.fusion?.limitations?.length ?? 0) > 0 ||
    evidence.provenance?.status === 'unavailable' ||
    ensemble?.abstained ||
    ensembleNotes.length > 0
  )

  return (
    <div className="space-y-5">
      {/* OBSERVED FACTS */}
      {hasFindings && (
        <ResultSection
          index="05"
          title={t('result.facts.title')}
          subtitle={t('result.facts.subtitle')}
        >
          <ul className="space-y-3">
            {evidence.fusion.findings.map((finding, index) => (
              <li
                key={`${finding.tier}-${finding.source}-${index}`}
                className="flex items-start gap-3 rounded-md border border-line/60 bg-surface-inset/30 p-3.5"
              >
                <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-signal/10 text-[0.6rem] font-medium text-signal">
                  {finding.tier}
                </span>
                <div className="min-w-0">
                  <p className="ltr-embed text-[0.76rem] text-signal font-medium">
                    {t('result.facts.findingTitle').replace('{tier}', String(finding.tier))}
                  </p>
                  <p className="font-arabic-body mt-0.5 text-[0.72rem] leading-relaxed text-text-muted">
                    {finding.claim}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </ResultSection>
      )}

      {/* MODEL INFERENCES */}
      {hasInferences && (
        <ResultSection
          index="06"
          title={t('result.inferences.title')}
          subtitle={t('result.inferences.subtitle')}
        >
          <div className="space-y-3">
            <p className="font-arabic-body text-[0.72rem] leading-relaxed text-text-muted">
              {t('result.inferences.preamble')}
            </p>
            {ensemble != null && ensemble.detectors.map((detector, index) => (
              <div
                key={detector.modelName + index}
                className={cn(
                  'flex items-start gap-3 rounded-md border p-3.5',
                  'border-signal/20 bg-surface-inset/30',
                )}
              >
                <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-signal/10 text-[0.6rem] font-medium text-signal">
                  {index + 1}
                </span>
                <div className="min-w-0">
                  <p className="ltr-embed text-[0.76rem] text-signal font-medium">
                    {detector.modelName}
                  </p>
                  <p className="font-arabic-body mt-0.5 text-[0.72rem] leading-relaxed text-text-muted">
                    {detector.architecture}
                  </p>
                  <p className="mono-label mt-1 text-[0.68rem] text-text-dim">
                    {t('result.inferences.probability')}: {(detector.syntheticProbability * 100).toFixed(1)}%
                  </p>
                </div>
              </div>
            ))}
            {ensemble != null && ensemble.notes != null && ensemble.notes.length > 0 && (
              <p className="font-arabic-body text-[0.72rem] leading-relaxed text-text-dim">
                {ensemble.notes.map((note, i) => (
                  <span key={i}>
                    · {note}
                    {i < ensemble.notes.length - 1 && <br />}
                  </span>
                ))}
              </p>
            )}
          </div>
        </ResultSection>
      )}

      {/* UNCERTAINTIES */}
      {hasUncertainties && (
        <ResultSection
          index="07"
          title={t('result.uncertainties.title')}
          subtitle={t('result.uncertainties.subtitle')}
        >
          <ul className="space-y-3">
            {evidence.fusion?.limitations.map((limitation, index) => (
              <li
                key={index}
                className="flex items-start gap-3 rounded-md border border-caution/20 bg-caution/5 p-3.5"
              >
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-caution/20 text-[0.55rem] font-medium text-caution">
                  !
                </span>
                <p className="font-arabic-body text-[0.72rem] leading-relaxed text-text">
                  {limitation}
                </p>
              </li>
            ))}
            {evidence.provenance?.status === 'unavailable' && (
              <li className="flex items-start gap-3 rounded-md border border-line/60 bg-surface-inset/30 p-3.5">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-text-dim/10 text-text-dim">
                  —
                </span>
                <p className="font-arabic-body text-[0.72rem] leading-relaxed text-text-muted">
                  {t('result.uncertainties.noProvenance')}
                </p>
              </li>
            )}
            {ensemble != null && ensemble.abstained && (
              <li className="flex items-start gap-3 rounded-md border border-line/60 bg-surface-inset/30 p-3.5">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-text-dim/10 text-text-dim">
                  —
                </span>
                <p className="font-arabic-body text-[0.72rem] leading-relaxed text-text-muted">
                  {t('result.uncertainties.abstained')}
                </p>
              </li>
            )}
          </ul>
        </ResultSection>
      )}
    </div>
  )
}
