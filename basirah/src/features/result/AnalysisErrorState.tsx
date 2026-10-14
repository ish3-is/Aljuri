import { motion } from 'motion/react'
import { RotateCcw, TriangleAlert } from 'lucide-react'
import { useI18n } from '../../i18n/useI18n'
import { Magnetic } from '../../components/ui/primitives'
import type { TranslationKey } from '../../i18n/translations'
import type { AnalysisError } from '../analysis/providers'

/**
 * Backend error codes that carry a known, user-actionable meaning.
 *
 * When a code appears here the raw server text is DISCARDED and the
 * curated bilingual message is shown instead. Backend exception
 * strings are written for developers — they can name internal paths,
 * library types and validation internals — and surfacing them to a
 * user of a trust product is both ugly and a mild information leak.
 *
 * An unmapped code falls through to the generic message rather than
 * to the raw text, so an unrecognised code can never leak either.
 */
const FRIENDLY_CODES: Record<string, TranslationKey> = {
  corrupt_image: 'image.errors.corrupt_image',
  not_an_image: 'image.errors.not_an_image',
  svg_not_supported: 'image.errors.svg_not_supported',
  unsupported_format: 'image.errors.unsupported_format',
  empty_file: 'image.errors.empty_file',
  file_too_large: 'image.errors.file_too_large',
  network_unavailable: 'image.errors.network_unavailable',
  analysis_failed: 'image.errors.analysis_failed',
}

/**
 * Analysis error state.
 *
 * Shown when a provider fails — the backend is down, the URL was
 * rejected, or the response was malformed.
 *
 * The important behaviour here is what this component does NOT do: it
 * does not fall back to mock data. A system that shows fabricated
 * intelligence because the real engine was unreachable would be worse
 * than one that admits it has no answer, and for a trust product that
 * distinction is the whole point.
 */
export function AnalysisErrorState({
  error,
  onReset,
}: {
  error: AnalysisError
  onReset: () => void
}) {
  const { language, t } = useI18n()
  const isArabic = language === 'ar'

  const copy = isArabic
    ? {
        title: 'تعذّر إكمال التحليل',
        offline: 'خدمة التحليل غير متاحة',
        rejected: 'لم يُقبل هذا الرابط',
        guidance:
          'لم يتم عرض أي نتائج. لم تستبدل بيانات المحاكاة بنتيجة حقيقية، لأن BASIRAH لا يعرض استخبارات غير مُتحقَّق منها.',
        retry: 'إعادة المحاولة',
        technical: 'رمز الخطأ',
      }
    : {
        title: 'Analysis could not be completed',
        offline: 'The analysis service is unavailable',
        rejected: 'This URL was not accepted for analysis',
        guidance:
          'No results are shown. Simulated data was not substituted for a real result, because BASIRAH does not present unverified intelligence.',
        retry: 'Try again',
        technical: 'Error code',
      }

  // Distinguish "we could not reach the engine" from "the engine
  // examined this and refused it" — they mean different things to a user.
  const isNetwork = error.code === 'network_unavailable'
  const isRejection =
    error.code === 'unsupported_scheme' ||
    error.code === 'url_too_long' ||
    error.code === 'invalid_host' ||
    error.code === 'missing_host' ||
    error.code === 'empty_url' ||
    error.code === 'invalid_port' ||
    error.code === 'unparsable' ||
    error.code === 'validation_error' ||
    error.code === 'missing_field'

  const heading = isNetwork
    ? copy.offline
    : isRejection
      ? copy.rejected
      : copy.title

  /**
   * Resolve the message. A known code wins over anything the server
   * said; otherwise the generic copy is used. `error.message` is
   * deliberately NOT rendered — see FRIENDLY_CODES.
   */
  const friendlyKey = FRIENDLY_CODES[error.code]
  const message = friendlyKey
    ? t(friendlyKey)
    : isArabic
      ? 'تعذّر إكمال التحليل. لم يتم عرض أي نتائج.'
      : 'The analysis could not be completed. No results are shown.'

  return (
    <motion.section
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 12 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="px-5 py-10 sm:px-8"
      role="alert"
      aria-live="assertive"
    >
      <div className="mx-auto max-w-2xl">
        <div className="rounded-lg border border-danger/25 bg-danger/[0.05] p-6 sm:p-8">
          <div className="flex items-start gap-4">
            <span className="mt-0.5 shrink-0 text-danger">
              <TriangleAlert size={20} />
            </span>
            <div className="min-w-0 flex-1">
              <h2 className="text-lg leading-snug font-light text-text">
                {heading}
              </h2>
              <p className="mt-2.5 text-[0.85rem] leading-relaxed text-text-muted">
                {message}
              </p>

              <p className="mt-4 text-[0.8rem] leading-relaxed text-text-dim">
                {copy.guidance}
              </p>

              <div className="mt-5 flex flex-wrap items-center gap-4">
                <Magnetic strength={5}>
                  <button
                    type="button"
                    onClick={onReset}
                    className="inline-flex items-center gap-2 rounded-full border border-line px-4 py-2 text-[0.78rem] text-text-muted transition-colors hover:border-line-bright hover:text-text"
                  >
                    <RotateCcw size={13} />
                    {copy.retry}
                  </button>
                </Magnetic>

                <span className="mono-label text-text-dim/70" dir="ltr">
                  {copy.technical}: {error.code}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </motion.section>
  )
}
