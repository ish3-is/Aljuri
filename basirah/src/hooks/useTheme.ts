import { useCallback, useSyncExternalStore } from 'react'

/* ============================================================
   THEME

   Three states are supported, not two, and the distinction matters:
     'light' | 'dark'  — the reader chose
     'system'          — follow the OS, change live if the OS changes

   An explicit choice is stored and always beats the system
   preference; a reader who picked light in daylight does not want
   their report inverted at dusk. 'system' is the default, and it is
   a real subscription rather than a one-time read, so an OS theme
   flip updates the page without a reload.

   The store is `document.documentElement`, exactly like the language
   hook: the DOM element IS the external state, and reading it
   through useSyncExternalStore guarantees no flash of the wrong
   theme on first paint.
   ============================================================ */

export type ThemePreference = 'light' | 'dark' | 'system'
export type ResolvedTheme = 'light' | 'dark'

const STORAGE_KEY = 'basirah.theme'

/** Listeners are notified by setTheme and by the OS media query. */
const listeners = new Set<() => void>()

function emit(): void {
  for (const listener of listeners) listener()
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener)

  const media = window.matchMedia('(prefers-color-scheme: dark)')
  media.addEventListener('change', listener)

  return () => {
    listeners.delete(listener)
    media.removeEventListener('change', listener)
  }
}

/** Read the preference, tolerating a denied or corrupted storage. */
function readPreference(): ThemePreference {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    if (stored === 'light' || stored === 'dark' || stored === 'system') {
      return stored
    }
  } catch {
    // Private mode. The system preference is still usable.
  }
  return 'system'
}

function systemTheme(): ResolvedTheme {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light'
}

/** Resolve the preference to the theme that should actually paint. */
export function resolveTheme(preference: ThemePreference): ResolvedTheme {
  if (preference === 'system') return systemTheme()
  return preference
}

/**
 * Apply the theme to the document.
 *
 * `data-theme` is what the CSS token layer keys off. It is set on the
 * root element, so every `var(--bas-*)` in the tree re-resolves in
 * one paint — no component re-renders and no class name changes.
 */
export function applyTheme(preference: ThemePreference): ResolvedTheme {
  const resolved = resolveTheme(preference)
  document.documentElement.dataset.theme = resolved
  return resolved
}

/** Exported for the inline bootstrap script in index.html. */
export function bootstrapTheme(): void {
  applyTheme(readPreference())
}

function getSnapshot(): ThemePreference {
  return readPreference()
}

/** No window (SSR / prerender): follow the system default. */
function getServerSnapshot(): ThemePreference {
  return 'system'
}

export function useTheme() {
  const preference = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)

  const resolved = resolveTheme(preference)

  const setTheme = useCallback((next: ThemePreference) => {
    try {
      window.localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // Non-fatal: the theme applies for this session regardless.
    }
    applyTheme(next)
    emit()
  }, [])

  /**
   * The header control is a two-state switch, not a three-way cycle:
   * "light / dark". 'system' is the initial value, and pressing the
   * toggle from it resolves to the OPPOSITE of what is currently on
   * screen, which is what a reader pressing a toggle means.
   */
  const toggleTheme = useCallback(() => {
    const current = resolveTheme(readPreference())
    setTheme(current === 'dark' ? 'light' : 'dark')
  }, [setTheme])

  return { preference, theme: resolved, setTheme, toggleTheme }
}