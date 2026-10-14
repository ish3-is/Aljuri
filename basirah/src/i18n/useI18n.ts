import { useContext } from 'react'
import { I18nContext, type I18nValue } from './context'

/**
 * Access the active language, direction and translator.
 *
 * Kept in its own module rather than exported from I18nProvider.tsx so
 * that provider file exports only a component, which is what React Fast
 * Refresh requires during development.
 */
export function useI18n(): I18nValue {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useI18n must be used inside <I18nProvider>')
  return ctx
}
