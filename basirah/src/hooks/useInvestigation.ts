import { useCallback, useEffect, useRef, useState } from 'react'
import { AnalysisError, resolveProvider } from '../features/analysis/providers'
import { recordAnalysis } from '../features/analysis/historyStore'
import { looksLikeUrl } from '../lib/utils'
import type {
  AnalysisProgress,
  AnalysisResult,
  InvestigationState,
  SignalKind,
  TimelineStageId,
} from '../types/analysis'

/** The submitted signal: text for URLs, an object URL for images. */
export interface Signal {
  kind: SignalKind
  /** Raw text for URL/text signals, filename for file signals. */
  label: string
  /** Preview URL for image signals; undefined for text. */
  previewUrl?: string
  /** Underlying file, forwarded to the real analyzer in later phases. */
  file?: File
}

const STAGE_SEQUENCE: TimelineStageId[] = [
  'acquire',
  'identify',
  'visual',
  'metadata',
  'url',
  'provenance',
  'synthetic',
  'correlate',
  'score',
]

/**
 * Which lanes light up for a given signal type. Mirrors the mock payload
 * but is computed from the signal so the UI animates the right branches
 * before any result exists.
 */
const LANES_BY_SIGNAL: Record<SignalKind, AnalysisResult['lanes']> = {
  url: ['url_intelligence', 'identity', 'metadata', 'provenance'],
  text: ['url_intelligence', 'identity'],
  image: ['synthetic_media', 'metadata', 'provenance', 'identity', 'fusion'],
  screenshot: ['synthetic_media', 'metadata', 'provenance', 'identity', 'fusion'],
  qr: ['synthetic_media', 'metadata', 'identity', 'fusion'],
  file: ['metadata', 'identity', 'url_intelligence', 'fusion'],
}

export interface Investigation {
  state: InvestigationState
  signal: Signal | null
  progress: AnalysisProgress
  result: AnalysisResult | null
  /** Set when a provider failed; drives an honest error state. */
  error: AnalysisError | null
  /** Submit a URL or image and run the analysis. */
  submit: (signal: Signal) => void
  /** Return to idle, releasing any object URL and aborting timers. */
  reset: () => void
  /** Track drag-over state on the whole core surface. */
  setDragging: (dragging: boolean) => void
}

const IDLE_PROGRESS: AnalysisProgress = {
  completed: 0,
  total: STAGE_SEQUENCE.length,
  activeStage: null,
  lanes: [],
}

/**
 * Owns the investigation lifecycle for the whole app.
 *
 * All timed work is tracked in a ref and cleared on unmount/reset, so a
 * reset mid-analysis can never leave a stage landing afterwards — the
 * classic stale-timer bug in staged async UI.
 */
export function useInvestigation(
  { pace = 380, reduced = false }: { pace?: number; reduced?: boolean } = {},
): Investigation {
  const [state, setState] = useState<InvestigationState>('idle')
  const [signal, setSignal] = useState<Signal | null>(null)
  const [progress, setProgress] = useState<AnalysisProgress>(IDLE_PROGRESS)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState<AnalysisError | null>(null)

  const timers = useRef<number[]>([])
  /** Monotonic id so a superseded run's stages stop applying. */
  const runId = useRef(0)
  const objectUrl = useRef<string | null>(null)

  const clearTimers = useCallback(() => {
    for (const id of timers.current) window.clearTimeout(id)
    timers.current = []
  }, [])

  const releaseObjectUrl = useCallback(() => {
    if (objectUrl.current) {
      URL.revokeObjectURL(objectUrl.current)
      objectUrl.current = null
    }
  }, [])

  useEffect(() => {
    return () => {
      clearTimers()
      releaseObjectUrl()
    }
  }, [clearTimers, releaseObjectUrl])

  /**
   * Resolve a completed analysis into terminal state.
   *
   * A failure is NOT silently swallowed and NOT replaced with a mock
   * result: showing fabricated intelligence because the backend was down
   * would be the single most damaging thing this product could do. The
   * UI is moved to an explicit error state instead.
   */
  const settle = useCallback(
    async (
      pending: Promise<
        { ok: true; result: AnalysisResult } | { ok: false; cause: unknown }
      >,
      currentRun: number,
    ) => {
      const outcome = await pending

      // A reset or a newer submission superseded this run.
      if (currentRun !== runId.current) return

      if (outcome.ok) {
        setResult(outcome.result)
        setError(null)
        setState('result')
        // Record the outcome for the Dashboard's local history.
        // Only a REAL completed analysis is recorded — a mock is
        // rejected inside recordAnalysis, so demo traffic can never
        // inflate the charts.
        recordAnalysis(outcome.result)
        return
      }

      const cause = outcome.cause
      setResult(null)
      setError(
        cause instanceof AnalysisError
          ? cause
          : new AnalysisError(
              cause instanceof Error ? cause.message : 'Analysis failed.',
              'analysis_failed',
            ),
      )
      setState('error')
    },
    [],
  )

  const submit = useCallback(
    async (nextSignal: Signal) => {
      clearTimers()
      releaseObjectUrl()

      const currentRun = ++runId.current

      // Take ownership of a freshly created preview URL so reset/unmount
      // can release it.
      if (nextSignal.previewUrl) objectUrl.current = nextSignal.previewUrl

      const lanes = LANES_BY_SIGNAL[nextSignal.kind] ?? LANES_BY_SIGNAL.url
      // Reduced motion collapses the cinematic sequence into a single
      // short beat: the state change still reads, without the procession.
      const stepDelay = reduced ? Math.min(pace, 160) : pace
      const stages = reduced
        ? (['acquire', 'correlate', 'score'] as TimelineStageId[])
        : STAGE_SEQUENCE.filter((stage) => {
            // URL signals skip visual-structure extraction, image signals
            // skip URL structure inspection — the journey reflects the
            // signal, it is not a fixed checklist.
            if (stage === 'visual') {
              return nextSignal.kind !== 'url' && nextSignal.kind !== 'text' &&
                nextSignal.kind !== 'file'
            }
            if (stage === 'url') {
              return nextSignal.kind === 'url' || nextSignal.kind === 'text' ||
                nextSignal.kind === 'file'
            }
            return true
          })

      setSignal(nextSignal)
      setResult(null)
      setError(null)
      setState('analyzing')
      setProgress({
        completed: 0,
        total: stages.length,
        activeStage: stages[0] ?? null,
        lanes,
      })

      // The real analysis starts now, in parallel with the staged
      // animation. A local pipeline answers in single-digit
      // milliseconds, so the cinematic sequence stays the pacing device
      // and the real payload is simply what lands at the end of it.
      const provider = resolveProvider(nextSignal.kind)
      const analysisPromise = provider
        .analyze(nextSignal)
        .then((result) => ({ ok: true as const, result }))
        .catch((cause: unknown) => ({ ok: false as const, cause }))

      stages.forEach((stage, index) => {
        const id = window.setTimeout(() => {
          if (currentRun !== runId.current) return

          setProgress((prev) => ({
            ...prev,
            completed: index + 1,
            activeStage: stage,
          }))

          if (index === stages.length - 1) void settle(analysisPromise, currentRun)
        }, stepDelay * (index + 1))
        timers.current.push(id)
      })
    },
    [clearTimers, pace, reduced, releaseObjectUrl, settle],
  )

  const reset = useCallback(() => {
    // Invalidate in-flight stages before clearing their timers.
    runId.current++
    clearTimers()
    releaseObjectUrl()
    setState('idle')
    setSignal(null)
    setResult(null)
    setError(null)
    setProgress(IDLE_PROGRESS)
  }, [clearTimers, releaseObjectUrl])

  const setDragging = useCallback((dragging: boolean) => {
    setState((prev) => {
      if (dragging) return prev === 'idle' ? 'dragging' : prev
      return prev === 'dragging' ? 'idle' : prev
    })
  }, [])

  return { state, signal, progress, result, error, submit, reset, setDragging }
}

/**
 * Classify raw user input without submitting it.
 *
 * A non-image upload is `file`, not `image`: the backend takes a
 * different branch for it (file intelligence instead of the image
 * ensemble), so mislabelling it here would send a text file down the
 * image pipeline and report an image failure for a text upload.
 */
export function detectSignalKind(value: string, file?: File): SignalKind {
  if (file) {
    const name = file.name.toLowerCase()
    if (name.includes('screenshot') || name.includes('لقطة')) return 'screenshot'
    if (file.type.startsWith('image/')) return 'image'
    return 'file'
  }
  return looksLikeUrl(value) ? 'url' : 'text'
}

/** Re-exported so callers can render the stage order without importing data. */
export { STAGE_SEQUENCE }
