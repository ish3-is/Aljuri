import { motion } from 'motion/react'
import { SectionLabel } from '../components/ui/primitives'
import { StateBadge } from '../components/ui/StateBadge'
import { detectionCategories } from '../data/detectionCategories'
import { useI18n } from '../i18n/useI18n'

/* ============================================================
   DETECTION CATEGORIES

   The full registry, honestly labelled. The primary modality spans
   two columns and carries the strongest border; the secondary one
   (Suspicious URLs) is visually equal to the rest rather than
   privileged, because it is the secondary modality — the ranking
   difference is expressed by the primary card's weight, not by
   diminishing the URL card.

   Planned entries are shown at full opacity on purpose. Hiding them
   would be the dishonest choice: a roadmap a visitor cannot see is a
   promise the platform will not be held to.
   ============================================================ */

export function CategoriesPage() {
  const { t } = useI18n()

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
            title={t('categories.title')}
            subtitle={t('categories.subtitle')}
            className="mb-10"
          />
        </motion.div>

        <div className="grid gap-4 md:grid-cols-2">
          {detectionCategories.map((category, index) => (
            <motion.article
              key={category.id}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-40px' }}
              transition={{ delay: (index % 3) * 0.06, duration: 0.55 }}
              className={
                category.primary
                  ? 'relative overflow-hidden rounded-lg border border-signal/30 bg-signal/[0.05] p-6 sm:p-8 md:col-span-2'
                  : 'relative overflow-hidden rounded-lg border border-line/70 bg-surface/40 p-6'
              }
            >
              {category.primary && (
                <span
                  aria-hidden
                  className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-signal/50 to-transparent"
                />
              )}

              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <p className="mono-label text-text-dim/70" dir="ltr">
                    {String(index + 1).padStart(2, '0')}
                  </p>
                  <h2
                    className={
                      category.primary
                        ? 'mt-2 text-xl font-light tracking-tight text-signal'
                        : 'mt-2 text-base font-light tracking-tight text-text'
                    }
                  >
                    {t(category.nameKey)}
                  </h2>
                </div>
                <StateBadge state={category.state} still />
              </div>

              <p className="mt-4 max-w-2xl text-[0.84rem] leading-relaxed text-text-muted">
                {t(category.bodyKey)}
              </p>

              <p className="mt-4 text-[0.68rem] text-text-dim">
                {t('categories.statusLabel')}: {t(`state.${category.state}`)}
              </p>
            </motion.article>
          ))}
        </div>
      </div>
    </div>
  )
}