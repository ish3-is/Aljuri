/**
 * React hook for the build-time delivery mode.
 *
 * Returns the resolved delivery mode through the React context owned by
 * `AppModeProvider`. `AppModeProvider` is rendered by `App` and is
 * guaranteed to wrap every component that calls this hook.
 */

import { useContext } from 'react'
import { AppModeContext, type AppModeContextValue } from './AppModeProvider'

/**
 * The resolved delivery mode for this build.
 *
 * Reading this hook outside `AppModeProvider` is a developer error.
 */
export function useAppMode(): AppModeContextValue {
  return useContext(AppModeContext)
}
