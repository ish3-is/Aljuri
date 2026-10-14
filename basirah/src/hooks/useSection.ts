import { useCallback, useSyncExternalStore } from 'react'
import { DEFAULT_SECTION, isSectionId, type SectionId } from '../app/sections'

/**
 * Hash-backed section state.
 *
 * `useSyncExternalStore` rather than `useState` + an effect: the URL
 * hash IS the external store here, so subscribing to it directly
 * removes the cascading-render problem an effect-based version has,
 * and guarantees the first paint already matches the hash (no flash of
 * the default section on a deep link).
 *
 * `hashchange` — rather than a History API push — keeps the browser
 * Back button working for free and means the active section survives a
 * reload or a shared link. An unknown hash falls back to the default
 * section instead of rendering an empty screen.
 */

function subscribe(onChange: () => void): () => void {
  window.addEventListener('hashchange', onChange)
  return () => window.removeEventListener('hashchange', onChange)
}

function readSection(): SectionId {
  if (typeof window === 'undefined') return DEFAULT_SECTION
  const raw = window.location.hash.replace(/^#\/?/, '')
  return isSectionId(raw) ? raw : DEFAULT_SECTION
}

export function useSection() {
  const section = useSyncExternalStore(subscribe, readSection, () => DEFAULT_SECTION)

  /**
   * Navigating to the section already active would push a duplicate
   * history entry that Back then has to step through twice, so it is
   * a no-op beyond returning to the top of that section.
   */
  const setSection = useCallback(
    (next: SectionId) => {
      if (next === readSection()) {
        window.scrollTo({ top: 0, behavior: 'smooth' })
        return
      }
      window.location.hash = `/${next}`
      // Scroll to top on a section change: keeping the previous
      // offset would drop the reader into the middle of a section
      // whose top they have not seen.
      window.scrollTo({ top: 0 })
    },
    [],
  )

  return { section, setSection }
}
