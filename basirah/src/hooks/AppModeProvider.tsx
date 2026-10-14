/**
 * Delivery-mode provider - a single React component.
 *
 * Resolves `VITE_APP_MODE` at build time and exposes isLocal / isShowcase
 * through React context so anything below it can read the mode without
 * knowing where it came from.
 */

import { createContext, useMemo } from 'react'
import { APP_MODE } from './appMode'

export interface AppModeContextValue {
  /** Whether this build is the full local runtime. */
  isLocal: boolean
  /** Whether this build is the static GitHub Pages showcase. */
  isShowcase: boolean
}

export const AppModeContext = createContext<AppModeContextValue>({
  isLocal: true,
  isShowcase: false,
})

export function AppModeProvider({ children }: { children: React.ReactNode }) {
  const value = useMemo(
    () => ({
      isLocal: APP_MODE === 'local',
      isShowcase: APP_MODE === 'showcase',
    }),
    [],
  )

  return (
    <AppModeContext.Provider value={value}>
      {children}
    </AppModeContext.Provider>
  )
}
