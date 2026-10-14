import { motion } from 'motion/react'
import { useI18n } from '../../i18n/useI18n'
import { SECTIONS, type SectionId } from '../../app/sections'
import { BasirahMark } from '../brand/BasirahMark'
import { UniversityAffiliation } from '../brand/UniversityAffiliation'

interface BasirahFooterProps {
  section: SectionId
  onNavigate: (section: SectionId) => void
}

/**
 * Institutional footer: identity, the canonical positioning sentence,
 * a section index, and the university mark.
 *
 * It repeats the positioning verbatim from `brand.positioning` rather
 * than summarising it — the footer is the last thing a visitor reads,
 * and it should describe the platform in exactly the same words as the
 * hero did.
 */
export function BasirahFooter({ section, onNavigate }: BasirahFooterProps) {
  const { t, tLatin } = useI18n()
  const year = new Date().getFullYear()

  return (
    <motion.footer
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true, margin: '-60px' }}
      transition={{ duration: 0.7 }}
      className="mt-24 border-t border-line/60"
    >
      <div className="mx-auto max-w-[1400px] px-5 py-12 sm:px-6">
        <div className="flex flex-col gap-10 lg:flex-row lg:items-start lg:justify-between">
          {/* Identity + positioning */}
          <div className="max-w-xl">
            <div className="flex items-center gap-3">
              <BasirahMark size={26} />
              <div className="leading-none">
                <p
                  dir="ltr"
                  className="text-[0.82rem] tracking-[0.14em] text-text-muted"
                >
                  {tLatin('brand.name')}
                </p>
                <p className="mt-1.5 text-[0.68rem] text-text-dim">
                  {t('brand.subtitle')}
                </p>
              </div>
            </div>
            <p className="mt-6 text-[0.78rem] leading-relaxed text-text-dim">
              {t('brand.positioning')}
            </p>
          </div>

          {/* Section index */}
          <nav aria-label={t('nav.label')} className="shrink-0">
            <p className="mono-label text-text-dim">{t('footer.explore')}</p>
            <ul className="mt-4 grid grid-cols-2 gap-x-8 gap-y-2.5">
              {SECTIONS.map((item) => (
                <li key={item.id}>
                  <a
                    href={`#/${item.id}`}
                    onClick={(event) => {
                      if (
                        event.metaKey ||
                        event.ctrlKey ||
                        event.shiftKey ||
                        event.button !== 0
                      ) {
                        return
                      }
                      event.preventDefault()
                      onNavigate(item.id)
                    }}
                    aria-current={section === item.id ? 'page' : undefined}
                    className="text-[0.78rem] text-text-dim transition-colors duration-200 hover:text-signal"
                  >
                    {t(item.labelKey)}
                  </a>
                </li>
              ))}
            </ul>
          </nav>

          {/* Academic affiliation */}
          <div className="shrink-0">
            <UniversityAffiliation width={150} />
          </div>
        </div>

        {/* Metadata line */}
        <div className="mt-10 flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-line/50 pt-6 text-[0.7rem] text-text-dim">
          <span>{t('footer.academicProject')}</span>
          <span aria-hidden className="text-line-bright">
            &middot;
          </span>
          <span dir="ltr">{tLatin('brand.name')}</span>
          <span aria-hidden className="text-line-bright">
            &middot;
          </span>
          <span dir="ltr">&copy; {year}</span>
        </div>
      </div>
    </motion.footer>
  )
}
