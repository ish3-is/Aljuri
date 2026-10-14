/**
 * Section model for the in-page router.
 *
 * The app is one route with seven sections rather than seven routes. A
 * real router was rejected deliberately: the platform is a single
 * document experience (an investigation in progress must survive moving
 * between Overview and Analyze), it deploys to a static host under an
 * arbitrary base path, and the section set is small and fixed. Adding
 * react-router would add a deep-link surface this build cannot honour
 * with server rewrites.
 *
 * The active section lives in the URL hash, so a section is still
 * linkable and the browser Back button works — the two properties that
 * actually matter for navigation.
 */

import type { TranslationKey } from '../i18n/translations'

export type SectionId =
  | 'overview'
  | 'categories'
  | 'analyze'
  | 'challenge'
  | 'capabilities'
  | 'dashboard'
  | 'reports'
  | 'team'
  | 'about'

export interface SectionDef {
  id: SectionId
  labelKey: TranslationKey
  /** Sections that host the investigation keep the core visual. */
  immersive?: boolean
}

/**
 * Render order. Overview leads (it is the landing view), Analyze sits
 * third because it is the primary action and must stay reachable in one
 * click from anywhere, and About closes the list.
 */
export const SECTIONS: SectionDef[] = [
  { id: 'overview', labelKey: 'nav.overview' },
  { id: 'categories', labelKey: 'nav.categories' },
  { id: 'analyze', labelKey: 'nav.analyze', immersive: true },
  // Internal defence mode: the same live pipeline plus a held-out
  // blind-test panel. Placed after Analyze because it is a working
  // surface for reviewers, not a primary visitor action.
  { id: 'challenge', labelKey: 'nav.challenge' },
  { id: 'capabilities', labelKey: 'nav.capabilities' },
  { id: 'dashboard', labelKey: 'nav.dashboard' },
  { id: 'reports', labelKey: 'nav.reports' },
  { id: 'team', labelKey: 'nav.team' },
  { id: 'about', labelKey: 'nav.about' },
]

export const DEFAULT_SECTION: SectionId = 'overview'

export function isSectionId(value: string): value is SectionId {
  return SECTIONS.some((section) => section.id === value)
}