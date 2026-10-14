import uniMark from '../../assets/university-of-bisha.png'
import { useI18n } from '../../i18n/useI18n'
import { cn } from '../../lib/utils'

/* ============================================================
   UNIVERSITY AFFILIATION

   The official mark of the University of Bisha (جامعة بيشة).

   Two facts about the asset drive this whole component:
     1. It is a WIDE wordmark — trimmed to 299x92, aspect 3.25 — so it
        is sized by WIDTH and its height follows. Rendering it in a
        square box (as the old badge did) crushed it to a fraction of
        its legible size and left most of the box empty.
     2. It is an institutional mark, not a sponsor mark. It is always
        rendered at reduced opacity and never larger than the BASIRAH
        lockup beside it, so the project stays the subject of the
        page.

   Aspect ratio is preserved exactly: the source is never recolored,
     never stretched, and the intrinsic width/height are always passed
     to the <img> so the browser reserves the correct box.
   ============================================================ */

interface UniversityAffiliationProps {
  /** Rendered width in px; height derives from the 299:92 ratio. */
  width?: number
  className?: string
  /** Hides the text block, leaving just the mark. */
  markOnly?: boolean
}

export function UniversityAffiliation({
  width = 132,
  className,
  markOnly = false,
}: UniversityAffiliationProps) {
  const { t } = useI18n()
  const height = Math.round(width * (92 / 299))

  return (
    <div className={cn('flex items-center gap-3.5', className)}>
      <img
        src={uniMark}
        alt=""
        width={width}
        height={height}
        loading="lazy"
        decoding="async"
        draggable={false}
        className="shrink-0 object-contain opacity-55 transition-opacity duration-300 hover:opacity-85"
        style={{ width, height }}
      />
      {!markOnly && (
        <div className="min-w-0">
          <p className="mono-label text-text-dim">{t('team.universityTitle')}</p>
          <p className="mt-1 text-[0.8rem] leading-snug text-text-muted">
            {t('team.universityName')}
          </p>
          <p className="mt-0.5 text-[0.68rem] leading-snug text-text-dim">
            {t('team.universitySub')}
          </p>
        </div>
      )}
    </div>
  )
}