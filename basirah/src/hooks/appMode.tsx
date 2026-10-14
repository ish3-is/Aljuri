/**
 * App mode - plain types and env values only. No React.
 *
 * Reads `VITE_APP_MODE` from the environment bundle at module load time
 * and exposes the resolved delivery mode. The value is read once on
 * import - it is a build artifact, not a runtime toggle.
 *
 * Supported values (case-insensitive, trimmed):
 *   local    - call the real backend; preserve full analysis.
 *   showcase - static frontend; no live API calls; demo/sample data.
 *
 * Also carries the `import.meta` augmentation Vite's `define` plugin
 * requires, so `VITE_APP_MODE` is substituted at build time.
 */

// --- import.meta augmentation (Vite define plugin) ---
// Type-augmented ImportMeta so Vite's `define` plugin substitutes the env
// vars into `import.meta.env.VITE_APP_MODE` at build time. Pure global
// declaration; no exports, so it never triggers fast-refresh rules.
interface ImportMetaEnv {
  VITE_APP_MODE?: string
  VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

// --- delivery-mode types and values (no React) ---

export type AppMode = 'local' | 'showcase'

export const APP_MODE_KEY = 'VITE_APP_MODE'
const SUPPORTED_MODES: AppMode[] = ['local', 'showcase']

function readModeFromEnv(): AppMode {
  if (typeof import.meta === 'undefined') return 'local'

  const raw = (import.meta as ImportMeta & { VITE_APP_MODE?: string })[APP_MODE_KEY]

  if (typeof raw !== 'string') return 'local'

  const trimmed = raw.trim().toLowerCase()
  return SUPPORTED_MODES.includes(trimmed as AppMode) ? (trimmed as AppMode) : 'local'
}

/** The resolved delivery mode.  Built at module load time from the
 *  environment bundle baked into the frontend by `npm run build`. */
export const APP_MODE: AppMode = readModeFromEnv()
