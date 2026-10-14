import { useI18n } from '../../i18n/useI18n'
import { cn } from '../../lib/utils'
import type {
  DistributionStatus,
  DetectorAgreement,
  ImageEvidenceQuality,
  ImageProvenanceDetail,
} from '../../types/analysis'

/** Status row for the result hero: one compact line of evidence
 * quality, distribution, provenance and detector agreement.
 */
interface EvidenceStatusRowProps {
  evidenceQuality: ImageEvidenceQuality
  distributionStatus: DistributionStatus
  provenance: ImageProvenanceDetail
  detectorAgreement: DetectorAgreement
}

export function EvidenceStatusRow({
  evidenceQuality,
  distributionStatus,
  provenance,
  detectorAgreement,
}: EvidenceStatusRowProps) {
   const { t, language } = useI18n()
   const isArabic = language === 'ar'

   const quality =
    t('result.evidenceQuality') +
    (evidenceQuality.longEdge ? ` — ${evidenceQuality.longEdge}px` : '') +
    (evidenceQuality.lowResolution ? ' · low resolution' : '') +
    (evidenceQuality.warnings?.length
      ? ` · ${evidenceQuality.warnings.length} warning(s)`
      : '')
   const distribution =
     distributionStatus === 'in_distribution'
       ? t('agreement.distributionStatus.in_distribution')
       : distributionStatus === 'borderline'
         ? t('agreement.distributionStatus.borderline')
         : distributionStatus === 'out_of_distribution'
           ? t('agreement.distributionStatus.out_of_distribution')
           : t('agreement.distributionStatus.unavailable')
   const provenanceStatus =
     provenance.status === 'verified'
       ? t('result.prov.statusVerified')
       : provenance.status === 'present_unverified'
         ? t('result.prov.statusPresentUnverified')
         : provenance.status === 'invalid'
           ? t('result.prov.statusInvalid')
           : t('result.prov.statusUnavailable')
   const agreement =
     detectorAgreement === 'strong_agreement'
       ? t('agreement.strong')
       : detectorAgreement === 'moderate_agreement'
         ? t('agreement.moderate')
         : detectorAgreement === 'insufficient'
           ? t('agreement.insufficient')
           : detectorAgreement === 'conflict'
             ? t('agreement.conflict')
             : t('agreement.unavailable')

  const rows = [
    { label: t('result.evidenceQuality'), value: quality },
    { label: t('result.distribution'), value: distribution },
    { label: t('result.prov.status'), value: provenanceStatus },
    { label: t('result.detectorAgreement'), value: agreement },
  ]

  return (
    <div
      className={cn(
        'flex flex-wrap gap-2 rounded-xl border border-line/40 bg-surface-inset/40 px-3 py-2',
        'text-[0.68rem]',
      )}
    >
      {rows.map((row) => (
        <div
          key={row.label}
          className="flex items-center gap-1.5 font-arabic-body"
        >
          <span className="text-text-dim">{row.label}:</span>
          <span
            className={cn(
              'font-arabic-body text-[0.72rem]',
              isArabic ? 'text-start' : 'text-start',
            )}
            dir="auto"
          >
            {row.value}
          </span>
        </div>
      ))}
    </div>
  )
}
