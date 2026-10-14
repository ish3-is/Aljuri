import { motion } from 'motion/react'
import { Panel, SectionLabel } from '../components/ui/primitives'
import { StateBadge } from '../components/ui/StateBadge'
import {
  activeCapabilities,
  limitedCapabilities,
  plannedCapabilities,
  type Capability,
} from '../data/capabilities'
import { useI18n } from '../i18n/useI18n'

/* ============================================================
   CAPABILITIES

   Two clearly separated groups — what works, and what does not yet.
   The split is structural rather than a filter on one list, because
   a reader scanning a single mixed list will assume every card in it
   is available.

   The image capability is listed first and rendered at a larger size
   in both groups; that ordering is the modality hierarchy.
   ============================================================ */

function CapabilityCard({
  capability,
  index,
}: {
  capability: Capability
  index: number
}) {
  const { t } = useI18n()
  const planned = capability.state === 'planned'
  // Limited modules get their own surface rather than the muted
  // planned styling, because "partially supported" is a stronger
  // claim than "not built" and must not look weaker than it is.
  const limited = capability.state === 'limited'

  return (
    <motion.article
      initial={{ opacity: 0, y: 14 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-40px' }}
      transition={{ delay: (index % 3) * 0.05, duration: 0.5 }}
      className={[
        'relative overflow-hidden rounded-lg border p-5',
        capability.primary
          ? 'border-signal/28 bg-signal/[0.05] sm:p-6'
          : limited
            ? 'border-caution/25 bg-caution/[0.04] sm:p-6'
            : planned
              ? 'border-line/60 bg-surface/25'
              : 'border-line/70 bg-surface/40',
      ].join(' ')}
    >
      <div className="flex items-start justify-between gap-4">
        <h3
          className={
            capability.primary
              ? 'text-[1.02rem] font-light tracking-tight text-signal'
              : 'text-[0.9rem] font-normal tracking-tight text-text'
          }
        >
          {t(capability.nameKey)}
        </h3>
        <StateBadge state={capability.state} still />
      </div>
      <p className="mt-3 text-[0.79rem] leading-relaxed text-text-dim">
        {t(capability.bodyKey)}
      </p>
    </motion.article>
  )
}

export function CapabilitiesPage() {
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
            title={t('capabilities.title')}
            subtitle={t('capabilities.subtitle')}
            className="mb-10"
          />
        </motion.div>

        {/* ---- What works today ---- */}
        <section>
          <div className="mb-5 flex items-center gap-3">
            <span className="mono-label text-trusted/80">01</span>
            <h2 className="text-sm text-text">
              {t('dashboard.activeModulesTitle')}
            </h2>
            <span aria-hidden className="hairline h-px flex-1" />
          </div>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {activeCapabilities.map((capability, index) => (
              <CapabilityCard
                key={capability.id}
                capability={capability}
                index={index}
              />
            ))}
          </div>
        </section>

        {/* ---- Partially supported ----
            C2PA gets its own section between the two, so a reader
            cannot mistake it for either a finished module or an
            unbuilt one. */}
        <section className="mt-14">
          <div className="mb-5 flex items-center gap-3">
            <span className="mono-label text-caution/80">02</span>
            <h2 className="text-sm text-text">
              {t('dashboard.limitedModulesTitle')}
            </h2>
            <span aria-hidden className="hairline h-px flex-1" />
          </div>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {limitedCapabilities.map((capability, index) => (
              <CapabilityCard
                key={capability.id}
                capability={capability}
                index={index}
              />
            ))}
          </div>
        </section>

        {/* ---- What is not ready ---- */}
        <section className="mt-14">
          <div className="mb-5 flex items-center gap-3">
            <span className="mono-label text-text-dim">03</span>
            <h2 className="text-sm text-text">
              {t('dashboard.plannedModulesTitle')}
            </h2>
            <span aria-hidden className="hairline h-px flex-1" />
          </div>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {plannedCapabilities.map((capability, index) => (
              <CapabilityCard
                key={capability.id}
                capability={capability}
                index={index}
              />
            ))}
          </div>
        </section>

        {/* ---- The framework that holds regardless of module state ---- */}
        <section className="mt-14">
          <Panel accent className="p-6 sm:p-8">
            <SectionLabel
              index="04"
              title={t('dashboard.trustFrameworkTitle')}
              subtitle={t('dashboard.trustFrameworkSub')}
              className="mb-7"
            />
            <div className="grid gap-6 md:grid-cols-3">
              {(
                [
                  ['dashboard.evidenceCorrelation', 'dashboard.trustCorrelationBody'],
                  ['dashboard.probabilistic', 'dashboard.trustProbabilisticBody'],
                  ['dashboard.advisoryOnly', 'dashboard.trustAdvisoryBody'],
                ] as const
              ).map(([titleKey, bodyKey], index) => (
                <motion.div
                  key={titleKey}
                  initial={{ opacity: 0, y: 10 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: '-40px' }}
                  transition={{ delay: index * 0.07, duration: 0.5 }}
                >
                  <p className="text-[0.88rem] text-text">{t(titleKey)}</p>
                  <p className="mt-2 text-[0.78rem] leading-relaxed text-text-dim">
                    {t(bodyKey)}
                  </p>
                </motion.div>
              ))}
            </div>
          </Panel>
        </section>
      </div>
    </div>
  )
}