import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { I18nContext, type I18nValue } from './context'
import {
  translations,
  type Direction,
  type Language,
  type TranslationKey,
} from './translations'

/**
 * Owns the active language and, with it, the document's `lang` and `dir`.
 *
 * Translation copy lives under one key per string. Each entry is either a
 * plain string (language-invariant, e.g. the brand mark) or a
 * { en, ar } pair, so screen authors write both languages next to each
 * other instead of maintaining two parallel trees.
 *
 * The context itself lives in ./context.ts, separate from this component,
 * so no module exports both a component and a non-component — which is
 * what keeps React Fast Refresh working in development.
 */
const STORAGE_KEY = 'basirah.language'

function resolve(tree: unknown, key: string): unknown {
  return key.split('.').reduce<unknown>((node, part) => {
    if (node && typeof node === 'object') {
      return (node as Record<string, unknown>)[part]
    }
    return undefined
  }, tree)
}

/**
 * First load is ENGLISH by deliberate product decision, not by browser
 * locale. This platform previously inferred Arabic from
 * `navigator.language`, which meant an Arabic-locale browser landed on
 * an RTL screen before the visitor had chosen anything — the default
 * silently decided the reading direction of the product. English/LTR is
 * now the entry state; Arabic is one click away in the header toggle and
 * stays fully functional.
 *
 * A previously *stored* preference still wins: once someone has chosen
 * Arabic, a reload must not undo that choice.
 */
function readInitialLanguage(): Language {
  if (typeof window === 'undefined') return 'en'
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    if (stored === 'ar' || stored === 'en') return stored
  } catch {
    // Storage can be denied (private mode). English is still the default.
  }
  return 'en'
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(readInitialLanguage)
  const direction: Direction = language === 'ar' ? 'rtl' : 'ltr'

  // The document element is the anchor for direction: it flips the layout
  // axis for the whole tree, including logical CSS properties and the
  // inline SVG components that resolve `dir` through CSS.
  useEffect(() => {
    const root = document.documentElement
    root.lang = language
    root.dir = direction
  }, [language, direction])

  const setLanguage = useCallback((lang: Language) => {
    setLanguageState(lang)
    try {
      window.localStorage.setItem(STORAGE_KEY, lang)
    } catch {
      // Private-mode storage denial is non-fatal: language just won't persist.
    }
  }, [])

  const toggleLanguage = useCallback(() => {
    setLanguage(language === 'en' ? 'ar' : 'en')
  }, [language, setLanguage])

  const value = useMemo<I18nValue>(() => {
    const tree = translations as unknown as Record<string, unknown>

    const read = (key: TranslationKey, lang: Language): string => {
      const found = resolve(tree, key)
      // Plain string: identical in both languages.
      if (typeof found === 'string') return found
      // Bilingual pair: { en, ar }.
      if (found !== null && typeof found === 'object') {
        const pair = found as Record<string, string>
        return pair[lang] ?? pair.en ?? ''
      }
      return ''
    }

    return {
      language,
      direction,
      isRtl: direction === 'rtl',
      setLanguage,
      toggleLanguage,
      t: (key) => read(key, language),
      tLatin: (key) => read(key, 'en'),
      pick: (entry) => entry[language],
    }
  }, [language, direction, setLanguage, toggleLanguage])

  return (
    <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
  )
}
