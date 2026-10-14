import { useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { ChevronDown } from 'lucide-react'
import { useI18n } from '../../i18n/useI18n'
import type { ImageModelDetail } from '../../types/analysis'

/* ============================================================
   MODEL DISCLOSURE CARD

   What produced this number, and what it may be used for.

   The status flags (Research-grade / Advisory only / Not fit for
   automated enforcement) are shown UNCONDITIONALLY. They are not
   behind the methodology disclosure, because a user who never opens
   the disclosure must still meet the limits of the model.

   What the disclosure reveals is the limitation prose supplied by
   the pipeline. Those statements are the most valuable and least
   flattering text in the product — they are the measured record of
   where this model fails — so they are revealed on request but not
   hidden: the toggle says plainly that they exist.

   NOT rendered here: the checkpoint filename, and any held-out
   accuracy figure. Both are internal artefacts / research metrics;
   the first is an implementation detail and the second would put a
   benchmark number in front of a user as if it described this image.
   ============================================================ */

interface ModelDisclosureCardProps {
  model: ImageModelDetail
}

export function ModelDisclosureCard({ model }: ModelDisclosureCardProps) {
  const { t, language } = useI18n()
  const isArabic = language === 'ar'
  const [open, setOpen] = useState(false)

  const hasLimitations = model.knownLimitations.length > 0
  const disclosureId = 'basirah-model-methodology'

  return (
    <div className="relative overflow-hidden rounded-lg border border-line/70 bg-surface/40 p-5">
      <span
        aria-hidden
        className="absolute inset-y-0 start-0 w-px bg-gradient-to-b from-intel/60 to-transparent"
      />

      <p className="mono-label text-text-dim">{t('image.model.title')}</p>

      {/* ---- Identity. The display name is fixed product copy; the
          backend's modelName is used only as a fallback when it
          differs, and the checkpoint is never surfaced. ---- */}
      <h3 className="mt-2.5 text-base leading-snug font-normal text-text">
        {model.modelName ?? t('image.model.name')}
      </h3>

      {/* ---- Unconditional status flags ---- */}
      <dl className="mt-4 flex flex-wrap gap-2">
        <div className="inline-flex items-center gap-2 rounded-full border border-caution/25 bg-caution/8 px-3 py-1">
          <span aria-hidden className="size-1 rounded-full bg-caution" />
          <span className="text-[0.68rem] tracking-[0.1em] text-caution/90 uppercase">
            {t('image.model.statusLabel')}: {t('image.model.statusValue')}
          </span>
        </div>
        {model.advisoryOnly && (
          <div className="inline-flex items-center gap-2 rounded-full border border-line-bright/60 px-3 py-1">
            <span aria-hidden className="size-1 rounded-full bg-text-dim" />
            <span className="text-[0.68rem] tracking-[0.1em] text-text-muted uppercase">
              {t('image.model.advisoryLabel')}
            </span>
          </div>
        )}
        {!model.fitForAutomatedEnforcement && (
          <div className="inline-flex items-center gap-2 rounded-full border border-danger/25 bg-danger/8 px-3 py-1">
            <span aria-hidden className="size-1 rounded-full bg-danger" />
            <span className="text-[0.68rem] tracking-[0.1em] text-danger/90 uppercase">
              {t('image.model.enforcementLabel')}
            </span>
          </div>
        )}
      </dl>

      {/* ---- Model unavailability, stated plainly ---- */}
      {!model.available && (
        <div className="mt-4 rounded-md border border-caution/25 bg-caution/[0.05] p-3.5">
          <p className="text-[0.78rem] font-normal text-caution/90">
            {t('image.model.unavailable')}
          </p>
          <p className="mt-1.5 text-[0.76rem] leading-relaxed text-text-muted">
            {t('image.model.unavailableBody')}
          </p>
        </div>
      )}

      {/* ---- Methodology, collapsed by default ---- */}
      <div className="mt-4">
        <button
          type="button"
          onClick={() => setOpen((prev) => !prev)}
          aria-expanded={open}
          aria-controls={disclosureId}
          className="inline-flex items-center gap-2 rounded-full border border-line px-3.5 py-1.5 text-[0.74rem] text-text-muted transition-colors hover:border-line-bright hover:text-text"
        >
          {open ? t('image.model.methodologyClose') : t('image.model.methodologyOpen')}
          <motion.span
            aria-hidden
            animate={{ rotate: open ? 180 : 0 }}
            transition={{ duration: 0.25 }}
            className="inline-flex"
          >
            <ChevronDown size={13} />
          </motion.span>
        </button>

        <AnimatePresence initial={false}>
          {open && (
            <motion.div
              id={disclosureId}
              key="methodology"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
              className="overflow-hidden"
            >
              <div className="mt-4 space-y-4 border-t border-line/50 pt-4">
                {/* ---- Model's own safety notice, verbatim ----
                    English in the payload; kept LTR. */}
                <p
                  dir="ltr"
                  className={`text-[0.76rem] leading-relaxed text-text-muted ${
                    isArabic ? 'text-start' : ''
                  }`}
                >
                  {isArabic ? model.noticeAr : model.noticeEn}
                </p>

                {/* ---- Scope: which generators were in and out ---- */}
                {(model.trainedFamilies?.length ?? 0) > 0 && (
                  <div>
                    <p className="text-[0.68rem] leading-tight text-signal/70">
                      {t('image.model.familiesLabel')}
                    </p>
                    <p className="mt-1.5 flex flex-wrap gap-1.5">
                      {model.trainedFamilies?.map((family) => (
                        <span
                          key={family}
                          className="rounded border border-line-bright/50 px-2 py-0.5 font-mono text-[0.68rem] text-text-muted"
                          dir="ltr"
                        >
                          {family}
                        </span>
                      ))}
                    </p>
                  </div>
                )}

                {model.evaluatedHeldOutFamily && (
                  <div>
                    <p className="text-[0.68rem] leading-tight text-signal/70">
                      {t('image.model.heldOutLabel')}
                    </p>
                    <p className="ltr-embed mt-1.5 text-[0.76rem] text-text-muted">
                      {model.evaluatedHeldOutFamily}
                    </p>
                  </div>
                )}

                {/* ---- Known limitations, verbatim ----
                    These carry research metrics in their text (accuracy
                    figures, family names). They are rendered exactly as
                    the pipeline wrote them: this is the disclosure, and
                    editing it would defeat its purpose. The UI displays no
                    research metric of its own accord. */}
                <div>
                  <p className="text-[0.68rem] leading-tight text-caution/80">
                    {t('image.model.limitationsTitle')}
                  </p>
                  {hasLimitations ? (
                    <ul className="mt-2 space-y-2">
                      {model.knownLimitations.map((limitation, index) => (
                        <motion.li
                          key={index}
                          initial={{ opacity: 0, x: 8 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: index * 0.06, duration: 0.3 }}
                          className="flex items-start gap-2.5"
                        >
                          <span
                            aria-hidden
                            className="mt-1.5 size-1 shrink-0 rounded-full bg-caution/70"
                          />
                          <p
                            dir="ltr"
                            className={`text-[0.76rem] leading-relaxed text-text-muted ${
                              isArabic ? 'text-start' : ''
                            }`}
                          >
                            {limitation}
                          </p>
                        </motion.li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-2 text-[0.76rem] text-text-dim">
                      {t('image.model.noLimitations')}
                    </p>
                  )}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}