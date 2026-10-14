import { motion } from 'motion/react'
import { useI18n } from '../../i18n/useI18n'
import type { TranslationKey } from '../../i18n/translations'
import type { ImageProvenanceDetail, ImageProvenanceStatus } from '../../types/analysis'

/* ============================================================
   IMAGE PROVENANCE PANEL

   The honest rendering of "can we establish where this came from".

   The single most important constraint here is that `verified` is
   the ONLY status that may be presented as verified. In particular
   this component never says "C2PA verified": the payload reports
   whether content credentials and a manifest were FOUND, and
   whether the manifest parsed. Finding credentials is not the same
   as verifying them, and the present_unverified state exists
   precisely to keep that distinction visible.

   `unavailable` is the common case — most images, including genuine
   camera photographs shared through platforms, carry no provenance
   data at all — and it is stated plainly rather than shown as an
   empty state or a zero.
   ============================================================ */

interface ImageProvenancePanelProps {
  provenance: ImageProvenanceDetail
}

const STATUS_KEY: Record<ImageProvenanceStatus, TranslationKey> = {
  verified: 'image.provenance.verified',
  present_unverified: 'image.provenance.presentUnverified',
  invalid: 'image.provenance.invalid',
  unavailable: 'image.provenance.unavailable',
}

const STATUS_COLOR: Record<ImageProvenanceStatus, string> = {
  verified: 'var(--color-trusted)',
  present_unverified: 'var(--color-caution)',
  invalid: 'var(--color-danger)',
  unavailable: 'var(--color-text-dim)',
}

export function ImageProvenancePanel({ provenance }: ImageProvenancePanelProps) {
  const { t, language } = useI18n()
  const isArabic = language === 'ar'

  const color = STATUS_COLOR[provenance.status]
  const present = t('image.metadata.present')
  const absent = t('image.metadata.absent')

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
      className="relative overflow-hidden rounded-lg border border-line/70 bg-surface/40 p-5"
    >
      <span
        aria-hidden
        className="absolute inset-y-0 start-0 w-px"
        style={{ background: color }}
      />

      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-2">
        <p className="mono-label text-text-dim">{t('image.provenance.title')}</p>
        <span
          className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[0.68rem] tracking-[0.12em] uppercase"
          style={{ color, borderColor: `${color}40`, background: `${color}12` }}
        >
          <span
            aria-hidden
            className="size-1 rounded-full"
            style={{ background: color }}
          />
          {t(STATUS_KEY[provenance.status])}
        </span>
      </div>

      {/* ---- What was actually found, as booleans ---- */}
      <dl className="mt-4 grid gap-x-6 gap-y-2.5 sm:grid-cols-2">
        <div className="flex items-baseline justify-between gap-3">
          <dt className="text-[0.78rem] text-text-dim">
            {t('image.provenance.credentials')}
          </dt>
          <dd className="text-[0.78rem] text-text-muted">
            {provenance.contentCredentialsPresent ? present : absent}
          </dd>
        </div>
        <div className="flex items-baseline justify-between gap-3">
          <dt className="text-[0.78rem] text-text-dim">
            {t('image.provenance.manifest')}
          </dt>
          <dd className="text-[0.78rem] text-text-muted">
            {provenance.manifestFound ? present : absent}
          </dd>
        </div>
      </dl>

      {/* ---- The limitation, verbatim from the backend ----
          `unavailable` leads with the explicit sentence rather than the
          backend's longer prose, so the absence is unmissable. */}
      <p className="mt-4 border-t border-line/50 pt-3.5 text-[0.8rem] leading-relaxed text-text-muted">
        {provenance.status === 'unavailable' && (
          <span className="block font-normal text-text">
            {t('image.provenance.unavailableBody')}
          </span>
        )}
        {isArabic ? provenance.limitationAr : provenance.limitationEn}
      </p>

      {/* Absence of verification is never dressed up as a pass. */}
      {provenance.status !== 'verified' && (
        <p className="mt-3 text-[0.72rem] leading-relaxed text-text-dim/80">
          {t('image.provenance.notChecked')}
        </p>
      )}
    </motion.div>
  )
}