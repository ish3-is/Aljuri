import { motion } from 'motion/react'
import { ShieldAlert } from 'lucide-react'
import { Panel, SectionLabel } from '../components/ui/primitives'
import { BasirahLogo } from '../components/brand/BasirahLogo'
import { UniversityAffiliation } from '../components/brand/UniversityAffiliation'
import { useI18n } from '../i18n/useI18n'
import type { TranslationKey } from '../i18n/translations'

/* ============================================================
   ABOUT / METHODOLOGY

   The reference page for the project: what it is, why images come
   first, how a result is produced, and — most importantly — what it
   cannot do.

   The limitations block is given equal visual weight to the
   capability copy on purpose. A methodology page that only describes
   strengths is marketing; naming the limits is what makes the rest
   of the platform's output trustworthy enough to act on.
   ============================================================ */

export function AboutPage() {
  const { t, tLatin } = useI18n()

  const narrative: { titleKey: TranslationKey; bodyKey: TranslationKey }[] = [
    { titleKey: 'about.whatTitle', bodyKey: 'about.whatBody' },
    { titleKey: 'about.objectiveTitle', bodyKey: 'about.objectiveBody' },
    { titleKey: 'about.orderTitle', bodyKey: 'about.orderBody' },
    { titleKey: 'about.methodTitle', bodyKey: 'about.methodBody' },
    { titleKey: 'about.contextTitle', bodyKey: 'about.contextBody' },
  ]

  return (
    <div className="px-5 pt-28 pb-10 sm:px-8 sm:pt-32">
      <div className="mx-auto max-w-[1400px]">
        {/* ---- Identity header ---- */}
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="flex flex-col items-center text-center"
        >
          <BasirahLogo height={124} scanning={false} />
          <h1 className="mt-9 text-2xl font-extralight tracking-tight sm:text-3xl">
            <span className="text-gradient-signal">{t('about.title')}</span>
          </h1>
          <p
            dir="ltr"
            className="mt-3 text-[0.68rem] tracking-[0.34em] text-text-dim"
          >
            {tLatin('brand.name')}
          </p>
          <p className="mx-auto mt-6 max-w-2xl text-sm leading-relaxed text-text-muted">
            {t('brand.positioning')}
          </p>
        </motion.div>

        {/* ---- Narrative ---- */}
        <div className="mt-16 grid gap-4 md:grid-cols-2">
          {narrative.map((section, index) => (
            <motion.section
              key={section.titleKey}
              initial={{ opacity: 0, y: 14 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-40px' }}
              transition={{ delay: (index % 2) * 0.06, duration: 0.55 }}
              className={
                index === 0
                  ? 'rounded-lg border border-line/70 bg-surface/40 p-6 md:col-span-2'
                  : 'rounded-lg border border-line/70 bg-surface/40 p-6'
              }
            >
              <h2 className="mono-label text-signal/75">
                {t(section.titleKey)}
              </h2>
              <p className="mt-3 text-[0.85rem] leading-relaxed text-text-muted">
                {t(section.bodyKey)}
              </p>
            </motion.section>
          ))}
        </div>

        {/* ---- Limitations: equal weight, not a footnote ---- */}
        <section className="mt-6">
          <Panel className="border-caution/20 p-6 sm:p-8">
            <div className="flex items-start gap-3.5">
              <ShieldAlert size={17} className="mt-0.5 shrink-0 text-caution" />
              <div className="min-w-0">
                <h2 className="text-[0.95rem] text-caution">
                  {t('about.limitsTitle')}
                </h2>
                <p className="mt-3 max-w-3xl text-[0.84rem] leading-relaxed text-text-muted">
                  {t('about.limitsBody')}
                </p>
              </div>
            </div>
          </Panel>
        </section>

        {/* ---- Standing advisory notice ---- */}
        <section className="mt-4">
          <div className="rounded-lg border border-signal/20 bg-signal/[0.04] p-6 sm:p-7">
            <p className="text-[0.85rem] text-signal">
              {t('about.advisoryNoticeTitle')}
            </p>
            <p className="mt-2.5 max-w-3xl text-[0.8rem] leading-relaxed text-text-muted">
              {t('about.advisoryNoticeBody')}
            </p>
          </div>
        </section>

        {/* ---- Academic context ---- */}
        <section className="mt-6">
          <Panel accent className="flex flex-col items-start gap-6 p-6 sm:flex-row sm:items-center sm:justify-between sm:p-8">
            <div className="min-w-0">
              <SectionLabel
                index="06"
                title={t('about.contextTitle')}
                className="mb-0"
              />
              <p className="mt-3 text-[0.88rem] text-text">
                {t('team.universityName')}
              </p>
              <p className="mt-1.5 text-[0.78rem] text-text-dim">
                {t('footer.academicProject')} · {t('team.universitySub')}
              </p>
            </div>
            <UniversityAffiliation width={168} markOnly className="shrink-0 sm:ps-6" />
          </Panel>
        </section>
      </div>
    </div>
  )
}