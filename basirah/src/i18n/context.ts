import { createContext } from 'react'
import type { Bilingual, Direction, Language, TranslationKey } from './translations'

/**
 * The i18n contract.
 *
 * Lives in its own module (separate from the provider component) so both
 * `I18nProvider.tsx` and `useI18n.ts` can import it without any file
 * exporting a non-component alongside a component — which is what breaks
 * React Fast Refresh in development.
 */
export interface I18nValue {
  language: Language
  direction: Direction
  isRtl: boolean
  setLanguage: (lang: Language) => void
  toggleLanguage: () => void
  /** Resolve a dotted key in the active language. */
  t: (key: TranslationKey) => string
  /** Same as `t` but guarantees English — for brand marks, URLs, ids. */
  tLatin: (key: TranslationKey) => string
  /** Pick the language-appropriate half of an inline pair. */
  pick: (entry: Bilingual) => string
}

export const I18nContext = createContext<I18nValue | null>(null)
