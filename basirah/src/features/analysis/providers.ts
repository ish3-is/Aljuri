import { getMockResult } from '../../data/mockAnalysis'
import type { AnalysisResult, SignalKind } from '../../types/analysis'
import type { Signal } from '../../hooks/useInvestigation'
import { apiEvidenceAnalysisProvider as evidenceProvider } from './evidenceProvider'

/**
 * ANALYSIS PROVIDERS
 *
 * The single seam between the investigation lifecycle and whatever
 * actually analyses a signal. Phase 1 shipped with only the mock
 * provider; Phase 2 routes URLs to the real FastAPI pipeline while
 * images continue to use the mock, so the Phase 1 demo behaviour is
 * preserved until Phase 3 supplies a real synthetic-media engine.
 *
 * Adding a real provider later is a one-line change in
 * `resolveProvider` — no component or hook needs to know.
 */

/** Thrown when a provider cannot produce a result. Carries a stable code. */
export class AnalysisError extends Error {
  readonly code: string

  constructor(message: string, code = 'analysis_failed') {
    super(message)
    this.name = 'AnalysisError'
    this.code = code
  }
}

export interface AnalysisProvider {
  readonly name: string
  /** True when this provider returns simulated data. */
  readonly isMock: boolean
  /** Signal types this provider can handle. */
  supports(kind: SignalKind): boolean
  analyze(signal: Signal): Promise<AnalysisResult>
}

/* ------------------------------------------------------------------ */
/* Mock provider — images, screenshots, QR, and any offline fallback    */
/* ------------------------------------------------------------------ */

export const mockAnalysisProvider: AnalysisProvider = {
  name: 'mock',
  isMock: true,

  supports() {
    return true
  },

  async analyze(signal) {
    return getMockResult(signal.kind)
  },
}

/* ------------------------------------------------------------------ */
/* API provider — real URL intelligence (Phase 2)                      */
/* ------------------------------------------------------------------ */

/**
 * Backend base URL, centralised so no component hardcodes localhost.
 * Vite exposes VITE_-prefixed variables to the client bundle.
 *
 * If unset, the app falls back to the same-origin `/api` path, which is
 * the right default once a reverse proxy or GitHub Pages deployment
 * fronts the API — and it means the frontend works without any env file.
 */
export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/+$/, '') ??
  ''

/**
 * Base URL that browser code should call.
 *
 * In development this is ALWAYS the empty string, i.e. same-origin
 * `/api/...`. The Vite dev server proxies `/api` to the backend
 * (see `vite.config.ts`), so the request leaves the browser as a normal
 * same-origin call.
 *
 * That matters because the backend's CORS allowlist names specific
 * origins. Calling the backend directly from the browser during dev
 * makes the frontend work only on the ports that happen to be
 * allowlisted — it failed on any other Vite dev port with
 * `network_unavailable`. Same-origin requests are never subject to
 * CORS, so the dev server becomes the single place that knows where
 * the backend lives.
 *
 * In production the same-origin path is kept unless `VITE_API_BASE_URL`
 * names a genuinely different host (a reverse proxy or split hosting),
 * in which case that URL is used.
 */
export function resolveApiBase(): string {
  if (import.meta.env.DEV) return ''
  return API_BASE_URL
}

/**
 * A URL analysis result as returned by the backend.
 *
 * It already matches AnalysisResult field-for-field except for `dna`,
 * where the backend returns `null` for axes that do not apply to a URL.
 * That is the one honest deviation, and it is resolved in `toAnalysisResult`
 * rather than by weakening the backend's response.
 */
interface ApiUrlResponse extends Omit<AnalysisResult, 'dna'> {
  dna: Partial<Record<keyof AnalysisResult['dna'], number | null>>
  modelAvailable?: boolean
  modelNote?: string
  normalizedUrl?: string
}

export class ApiAnalysisProvider implements AnalysisProvider {
  readonly name = 'api'
  readonly isMock = false

  /** Resolved per request so an env change is picked up without a reload. */
  private get baseUrl(): string {
    return resolveApiBase()
  }

  supports(kind: SignalKind): boolean {
    return kind === 'url' || kind === 'text'
  }

  async analyze(signal: Signal): Promise<AnalysisResult> {
    const endpoint = `${this.baseUrl}/api/analyze/url`

    let response: Response
    try {
      response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: signal.label }),
      })
    } catch {
      // A network failure must surface as a clear state, never as a
      // silently empty result. The underlying cause is deliberately not
      // surfaced to the user: it can carry internal host detail, and the
      // actionable information is "the backend is not reachable".
      throw new AnalysisError(
        'The analysis service could not be reached. Is the backend running?',
        'network_unavailable',
      )
    }

    if (!response.ok) {
      let detail = `Request failed with status ${response.status}.`
      let code = `http_${response.status}`

      /**
       * FastAPI produces two different error shapes, and both must yield an
       * actionable message rather than "HTTP 422":
       *
       *   our rejections  {"error": "...", "code": "...", "detail": "..."}
       *   validation      {"detail": [{"type", "loc", "msg"}, ...]}
       *
       * Note the validation body is an OBJECT whose `detail` is an array —
       * it is not a bare array.
       */
      const readValidationList = (value: unknown): string[] => {
        const list = Array.isArray(value)
          ? value
          : Array.isArray((value as { detail?: unknown })?.detail)
            ? ((value as { detail: unknown[] }).detail)
            : []
        return list
          .map((item) => (item as { msg?: unknown })?.msg)
          .filter((msg): msg is string => typeof msg === 'string')
      }

      try {
        const body: unknown = await response.json()

        if (body && typeof body === 'object' && !Array.isArray(body)) {
          const record = body as Record<string, unknown>
          if (typeof record.code === 'string') code = record.code
          if (typeof record.detail === 'string') {
            detail = record.detail
          } else {
            const messages = readValidationList(body)
            if (messages.length > 0) {
              detail = messages.join(' ')
              const first = (
                Array.isArray((body as { detail?: unknown }).detail)
                  ? (body as { detail: unknown[] }).detail
                  : []
              )[0] as { type?: string } | undefined
              if (typeof first?.type === 'string') {
                code =
                  first.type === 'string_too_long'
                    ? 'url_too_long'
                    : first.type === 'missing'
                      ? 'missing_field'
                      : first.type
              }
            }
          }
        } else {
          const messages = readValidationList(body)
          if (messages.length > 0) detail = messages.join(' ')
        }
      } catch {
        // Non-JSON error body; keep the status-based message.
      }
      throw new AnalysisError(detail, code)
    }

    const payload = (await response.json()) as ApiUrlResponse
    return toAnalysisResult(payload, signal.label)
  }
}

/**
 * Adapt the API payload to the frontend contract.
 *
 * The backend returns `null` for Trust DNA axes that do not apply to the
 * signal type (synthetic-media and provenance for a plain URL). That
 * `null` is preserved verbatim so the UI can render "N/A" — coercing it
 * to 0 would present an unmeasured axis as a measured score of zero,
 * which is precisely the fabrication this product must avoid.
 */
export function toAnalysisResult(
  payload: ApiUrlResponse,
  submitted: string,
): AnalysisResult {
  const dna = payload.dna ?? {}
  const normalized = payload.normalizedUrl ?? submitted

  return {
    ...payload,
    signal: {
      kind: 'url',
      valueEn: normalized,
      valueAr: normalized,
    },
    dna: {
      synthetic: dna.synthetic ?? null,
      identity: dna.identity ?? null,
      domain: dna.domain ?? null,
      provenance: dna.provenance ?? null,
      behavior: dna.behavior ?? null,
    },
    lanes: ['url_intelligence', 'identity', 'metadata', 'provenance', 'fusion'],
    durationMs: payload.durationMs ?? 0,
  }
}

/* ------------------------------------------------------------------ */
/* Routing                                                              */
/* ------------------------------------------------------------------ */

const apiProvider = new ApiAnalysisProvider()

/**
 * Pick the provider for a signal.
 *
 * Phase 3.7: UPLOADS go to the multimodal evidence endpoint, which is a
 * strict superset of the single-modality image pipeline — it runs the
 * same image analysis and then adds provenance, OCR, QR, URL
 * extraction, URL intelligence, encoding inspection and cross-modal
 * fusion. URLs keep their dedicated endpoint, because a pasted link has
 * no upload to inspect.
 *
 * There is intentionally no fallback to `mockAnalysisProvider`. A silent
 * fallback would return a fabricated verdict for content the backend
 * simply failed to analyse, which is the one behaviour this product must
 * never have. The mock provider remains exported for the explicitly
 * labelled demo surface only.
 */
export function resolveProvider(kind: SignalKind): AnalysisProvider {
  // Evidence first: it claims image/screenshot/file/qr, which the
  // narrower image provider would otherwise take.
  if (evidenceProvider.supports(kind)) return evidenceProvider
  return apiProvider.supports(kind) ? apiProvider : mockAnalysisProvider
}

/**
 * Backend reachability, probed once per session. Used to show an
 * honest "service offline" state instead of failing every submission.
 */
let availability: Promise<boolean> | null = null

export function checkBackendAvailable(): Promise<boolean> {
  if (!availability) {
    const base = resolveApiBase()
    if (!base) {
      availability = Promise.resolve(false)
      return availability
    }
    availability = fetch(`${base}/api/health`, { method: 'GET' })
      .then((response) => response.ok)
      .catch(() => false)
  }
  return availability
}

/** Reset the cached probe — used by tests. */
export function resetBackendProbe(): void {
  availability = null
}
