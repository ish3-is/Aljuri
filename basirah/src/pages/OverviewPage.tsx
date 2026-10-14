import { motion } from 'motion/react'
import {
  ArrowRight,
  Boxes,
  FileSearch,
  Link2,
  ScanSearch,
} from 'lucide-react'
import { IntelligenceFrame } from '../components/brand/IntelligenceFrame'
import { UniversityAffiliation } from '../components/brand/UniversityAffiliation'
import { Magnetic, Panel, SectionLabel } from '../components/ui/primitives'
import { StateBadge } from '../components/ui/StateBadge'
import { detectionCategories } from '../data/detectionCategories'
import { activeCapabilities, plannedCapabilities } from '../data/capabilities'
import { useI18n } from '../i18n/useI18n'
import type { SectionId } from '../app/sections'

/* ============================================================
   OVERVIEW — the landing section.

   Composition follows the argument the product makes: identity and
   positioning first, then the image-first/URL-second hierarchy stated
   explicitly, then the two CTAs, then proof of scope (categories),
   capability, team preview and the academic affiliation.

   The hierarchy is expressed in four consistent ways, so it survives
   a skim:
     · ORDER    — image actions precede link actions everywhere
     · WEIGHT   — image cards are larger and carry a state badge;
                  link cards are a supporting column
     · COPY     — every sentence names images before links
     · MOTION   — the logo centerpiece is the primary signal
   ============================================================ */

interface OverviewProps {
  onNavigate: (section: SectionId) => void
}

export function OverviewPage({ onNavigate }: OverviewProps) {
  const { t, tLatin } = useI18n()

  /** Quick actions. Image leads; the link action is visibly secondary. */
  const quickActions = [
    {
      icon: ScanSearch,
      titleKey: 'overview.actionAnalyzeImage',
      subKey: 'overview.actionAnalyzeImageSub',
      target: 'analyze' as SectionId,
      primary: true,
    },
    {
      icon: Link2,
      titleKey: 'overview.actionAnalyzeLink',
      subKey: 'overview.actionAnalyzeLinkSub',
      target: 'analyze' as SectionId,
      primary: false,
    },
    {
      icon: Boxes,
      titleKey: 'overview.actionCategories',
      subKey: 'overview.actionCategoriesSub',
      target: 'categories' as SectionId,
      primary: false,
    },
    {
      icon: FileSearch,
      titleKey: 'overview.actionMethodology',
      subKey: 'overview.actionMethodologySub',
      target: 'about' as SectionId,
      primary: false,
    },
  ] as const

  return (
    <div className="px-5 pt-28 pb-6 sm:px-8 sm:pt-32">
      <div className="mx-auto flex max-w-[1400px] flex-col items-center">
        {/* ================= HERO ================= */}
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="w-full text-center"
        >
          <p className="mono-label text-text-dim">{t('overview.eyebrow')}</p>
          <p
            dir="ltr"
            className="mt-3 text-[0.68rem] tracking-[0.4em] text-signal/70"
          >
            {tLatin('brand.name')}
          </p>
        </motion.div>

        {/* --- The brand centerpiece, inside the intelligence frame.
            The frame is the platform's argument in one object: the
            mark at the centre, the six modalities it investigates
            around the perimeter, and the scanner reading across it.
            Sized in viewport-relative units so it never eats a
            phone's first screen. --- */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1.1, ease: [0.16, 1, 0.3, 1] }}
          className="mt-8 w-full max-w-[440px]"
        >
          <IntelligenceFrame />
        </motion.div>

        {/* --- Positioning: the canonical sentence, unmodified --- */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
          className="mt-14 w-full max-w-3xl"
        >
          <h1 className="font-arabic-display text-3xl leading-[1.15] font-extralight tracking-tight sm:text-4xl md:text-[2.9rem]">
            <span className="text-gradient-signal">{t('brand.tagline')}</span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-sm leading-relaxed text-text-muted sm:text-[0.95rem]">
            {t('brand.positioning')}
          </p>

          {/* The hierarchy, stated rather than implied */}
          <div className="mt-8 border-s border-line/60 ps-4 text-start">
            <p className="text-[0.9rem] font-normal text-text">
              {t('overview.valueTitle')}
            </p>
            <p className="mt-2 text-[0.82rem] leading-relaxed text-text-dim">
              {t('overview.valueBody')}
            </p>
          </div>
        </motion.div>

        {/* --- CTAs: primary image action, secondary exploration --- */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.34, duration: 0.8 }}
          className="mt-10 flex flex-wrap items-center justify-center gap-3"
        >
          <Magnetic strength={6}>
            <button
              type="button"
              onClick={() => onNavigate('analyze')}
              className="inline-flex items-center gap-2 rounded-full border border-signal/40 bg-signal/12 px-6 py-3 text-sm font-medium text-signal transition-colors duration-200 hover:border-signal/60 hover:bg-signal/18"
            >
              <ScanSearch size={16} />
              {t('overview.actionAnalyzeImage')}
              <ArrowRight size={15} className="rtl:-scale-x-100" />
            </button>
          </Magnetic>

          <Magnetic strength={4}>
            <button
              type="button"
              onClick={() => onNavigate('capabilities')}
              className="inline-flex items-center gap-2 rounded-full border border-line bg-surface-raised/50 px-6 py-3 text-sm text-text-muted transition-colors duration-200 hover:border-line-bright hover:text-text"
            >
              {t('overview.secondaryCta')}
            </button>
          </Magnetic>
        </motion.div>

        {/* ================= QUICK ACTIONS ================= */}
        <section className="mt-24 w-full">
          <SectionLabel
            index="01"
            title={t('overview.quickActionsTitle')}
            subtitle={t('overview.quickActionsSub')}
          />
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {quickActions.map((action, index) => {
              const Icon = action.icon
              return (
                <motion.button
                  key={action.titleKey}
                  type="button"
                  onClick={() => onNavigate(action.target)}
                  initial={{ opacity: 0, y: 14 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: '-40px' }}
                  transition={{ delay: index * 0.05, duration: 0.5 }}
                  className={action.primary
                    ? 'group relative overflow-hidden rounded-lg border border-signal/28 bg-signal/[0.05] p-5 text-start transition-colors duration-200 hover:border-signal/50'
                    : 'group relative overflow-hidden rounded-lg border border-line/70 bg-surface/40 p-5 text-start transition-colors duration-200 hover:border-line-bright'}
                >
                  <span
                    className={action.primary
                      ? 'text-signal'
                      : 'text-text-dim transition-colors group-hover:text-text-muted'}
                  >
                    <Icon size={17} />
                  </span>
                  <p
                    className={`mt-3.5 text-[0.9rem] ${action.primary ? 'text-signal' : 'text-text'}`}
                  >
                    {t(action.titleKey)}
                  </p>
                  <p className="mt-1.5 text-[0.72rem] leading-relaxed text-text-dim">
                    {t(action.subKey)}
                  </p>
                  {action.primary && (
                    <span
                      aria-hidden
                      className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-signal/50 to-transparent"
                    />
                  )}
                </motion.button>
              )
            })}
          </div>
        </section>

        {/* ================= DETECTION CATEGORIES PREVIEW ================= */}
        <section className="mt-20 w-full">
          <SectionLabel
            index="02"
            title={t('categories.title')}
            subtitle={t('categories.subtitle')}
          />
          <div className="grid gap-3 md:grid-cols-2">
            {detectionCategories.map((category, index) => (
              <motion.article
                key={category.id}
                initial={{ opacity: 0, y: 12 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-40px' }}
                transition={{ delay: (index % 4) * 0.05, duration: 0.5 }}
                className={category.primary
                  ? 'rounded-lg border border-signal/25 bg-signal/[0.04] p-5 md:col-span-2'
                  : 'rounded-lg border border-line/70 bg-surface/40 p-5'}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <p
                      className={category.primary
                        ? 'text-[0.95rem] text-signal'
                        : 'text-[0.88rem] text-text'}
                    >
                      {t(category.nameKey)}
                    </p>
                    <p className="mt-2 text-[0.78rem] leading-relaxed text-text-dim">
                      {t(category.bodyKey)}
                    </p>
                  </div>
                  <StateBadge state={category.state} still />
                </div>
              </motion.article>
            ))}
          </div>
        </section>

        {/* ================= CAPABILITIES PREVIEW ================= */}
        <section className="mt-20 w-full">
          <SectionLabel index="03" title={t('capabilities.title')} />
          <div className="grid gap-3 lg:grid-cols-3">
            {[...activeCapabilities, ...plannedCapabilities]
              .slice(0, 6)
              .map((capability, index) => (
                <motion.div
                  key={capability.id}
                  initial={{ opacity: 0, y: 12 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: '-40px' }}
                  transition={{ delay: (index % 3) * 0.05, duration: 0.5 }}
                  className="rounded-lg border border-line/70 bg-surface/40 p-5"
                >
                  <p className="text-[0.85rem] text-text">
                    {t(capability.nameKey)}
                  </p>
                  <p className="mt-2 text-[0.75rem] leading-relaxed text-text-dim">
                    {t(capability.bodyKey)}
                  </p>
                  <div className="mt-3.5">
                    <StateBadge state={capability.state} still />
                  </div>
                </motion.div>
              ))}
          </div>
        </section>

        {/* ================= TEAM PREVIEW + AFFILIATION ================= */}
        <section className="mt-20 w-full">
          <SectionLabel index="04" title={t('team.previewTitle')} />
          <Panel className="flex flex-col gap-6 p-6 sm:flex-row sm:items-center sm:justify-between sm:p-7">
            <div className="min-w-0">
              <p className="text-[0.95rem] text-text">{t('team.title')}</p>
              <p className="mt-2 max-w-md text-[0.8rem] leading-relaxed text-text-dim">
                {t('team.subtitle')}
              </p>
              <button
                type="button"
                onClick={() => onNavigate('team')}
                className="mt-5 inline-flex items-center gap-2 rounded-full border border-line px-4 py-2 text-[0.78rem] text-text-muted transition-colors hover:border-line-bright hover:text-text"
              >
                {t('team.viewTeam')}
                <ArrowRight size={13} className="rtl:-scale-x-100" />
              </button>
            </div>
            <UniversityAffiliation width={150} className="shrink-0 sm:ps-4" />
          </Panel>
        </section>
      </div>
    </div>
  )
}