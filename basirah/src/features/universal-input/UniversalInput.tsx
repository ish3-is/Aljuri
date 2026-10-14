import { AnimatePresence, motion } from 'motion/react'
import { FileText, Link2, Upload, X } from 'lucide-react'
import { useCallback, useRef, useState } from 'react'
import { useDragZone } from '../../hooks/useEnvironment'
import { detectSignalKind, type Signal } from '../../hooks/useInvestigation'
import { useI18n } from '../../i18n/useI18n'
import { EXAMPLE_URL } from '../../data/mockAnalysis'
import { cn } from '../../lib/utils'
import { Magnetic } from '../../components/ui/primitives'
import type { InvestigationState } from '../../types/analysis'

/* ============================================================
   UNIVERSAL INPUT

   One drop zone, two intake paths. The user never chooses a scanner:
   BASIRAH infers the signal type from what was submitted. What the
   user DOES choose, via the `modality` prop from the workspace
   selector, is which affordance leads the layout.

   That is the whole expression of the image-first / URL-second
   hierarchy at the input layer: field order and border emphasis
   follow `modality`, while the underlying intake paths stay
   identical. Image is the default because it is the platform's
   primary modality — a visitor who never touches the selector still
   gets the image-first layout.
   ============================================================ */

/**
 * Four intake modes.
 *
 * Image and Screenshot are separate entries even though both end up
 * on the evidence endpoint: the backend resolves the actual mode from
 * the bytes and REPORTS any contradiction between the requested mode
 * and the content, so choosing Screenshot for an image produces an
 * explicit note rather than a silent reinterpretation. File is
 * genuinely different — it takes the file-intelligence branch.
 *
 * URL is the secondary modality and the only one with no upload.
 */
export type Modality = 'image' | 'screenshot' | 'file' | 'url'

interface UniversalInputProps {
  state: InvestigationState
  signal: Signal | null
  /** Which affordance leads the layout. Image is the primary modality. */
  modality?: Modality
  onSubmit: (signal: Signal) => void
  onReset: () => void
  onDragStateChange: (dragging: boolean) => void
}

export function UniversalInput({
  state,
  signal,
  modality = 'image',
  onSubmit,
  onReset,
  onDragStateChange,
}: UniversalInputProps) {
  const { t } = useI18n()
  const [value, setValue] = useState('')
  const [dragging, setDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const isBusy = state === 'analyzing'
  const hasSignal = Boolean(signal)
  const isResult = state === 'result'
  const isUrlMode = modality === 'url'

  /** Shared intake path for drag-drop, file picker and clipboard. */
  const acceptFile = useCallback(
    (file: File) => {
      const kind = detectSignalKind(file.name, file)
      onSubmit({
        kind,
        label: file.name,
        file,
        previewUrl: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined,
      })
    },
    [onSubmit],
  )

  const dragHandlers = useDragZone(
    acceptFile,
    (isDraggingNow) => {
      setDragging(isDraggingNow)
      onDragStateChange(isDraggingNow)
    },
  )

  const handleSubmitUrl = useCallback(() => {
    const trimmed = value.trim()
    if (!trimmed || isBusy) return
    onSubmit({ kind: detectSignalKind(trimmed), label: trimmed })
  }, [value, isBusy, onSubmit])

  const loadExample = useCallback(() => {
    setValue(EXAMPLE_URL)
    onSubmit({ kind: 'url', label: EXAMPLE_URL })
  }, [onSubmit])

  const openFilePicker = useCallback(() => {
    fileInputRef.current?.click()
  }, [])

  /* ---------------- Primary / secondary affordances ---------------- */

  const ACCEPTED = {
    image: 'image/*',
    screenshot: 'image/*',
    file: 'image/*,.txt,.md,.csv,.json,.log,.yaml,.yml,.xml,.html,.htm,.py,.js,.ts,.ini,.cfg,.conf,.rtf',
    url: 'image/*',
  } as const

  const uploadAffordance = (
    <button
      type="button"
      onClick={openFilePicker}
      disabled={isBusy}
      className={cn(
        'flex w-full items-center gap-3.5 rounded-lg border px-4 py-4 text-start transition-colors duration-200',
        'disabled:opacity-40',
        isUrlMode
          ? 'border-line bg-surface-raised/50 hover:border-line-bright'
          : 'border-signal/40 bg-signal/[0.07] hover:border-signal/60',
      )}
    >
      <span className={isUrlMode ? 'text-text-dim' : 'text-signal'}>
        <Upload size={17} />
      </span>
      <span className="min-w-0">
        <span
          className={cn('block text-sm', isUrlMode ? 'text-text-muted' : 'text-signal')}
        >
          {t('input.fileButton')}
        </span>
        <span className="font-arabic-body mt-0.5 block text-[0.7rem] leading-relaxed text-text-dim">
          {t('input.acceptHint')}
        </span>
      </span>
    </button>
  )

  const urlAffordance = (
    <div className="flex items-stretch gap-2">
      <input
        type="text"
        inputMode="url"
        dir="ltr"
        value={value}
        disabled={isBusy}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter') handleSubmitUrl()
        }}
        placeholder={t('input.placeholder')}
        aria-label={t('input.placeholder')}
        className={cn(
          'w-full rounded-lg border bg-surface-inset/80 px-4 py-3',
          'font-mono text-sm text-text placeholder:text-text-dim/70',
          'transition-colors duration-200 focus:outline-none disabled:opacity-50',
          isUrlMode
            ? 'border-line/70 focus:border-line-bright'
            : 'border-signal/35 focus:border-signal/50',
        )}
      />
      <Magnetic strength={4}>
        <button
          type="button"
          onClick={handleSubmitUrl}
          disabled={isBusy || !value.trim()}
          className={cn(
            'inline-flex shrink-0 items-center gap-2 rounded-lg border px-4 py-3 text-sm transition-all duration-200',
            'disabled:pointer-events-none disabled:opacity-35',
            isUrlMode
              ? 'border-signal/35 bg-signal/10 text-signal hover:border-signal/55 hover:bg-signal/16'
              : 'border-line bg-surface-raised/60 text-text-muted hover:border-line-bright hover:text-text',
          )}
        >
          {t('actions.analyze')}
        </button>
      </Magnetic>
    </div>
  )

  return (
    <div
      className="w-full"
      // The whole zone is the drop target and the paste sink.
      {...dragHandlers}
    >
      <motion.div
        animate={{
          scale: dragging ? 1.015 : 1,
        }}
        transition={{ type: 'spring', stiffness: 300, damping: 28 }}
        className={cn(
          'relative overflow-hidden rounded-xl border transition-colors duration-300',
          dragging
            ? 'border-signal/60 bg-signal/[0.06]'
            : 'border-line/80 bg-surface/40 hover:border-line-bright',
        )}
      >
        {/* Drag affordance: a bright inset ring that closes in on release */}
        <AnimatePresence>
          {dragging && (
            <motion.span
              aria-hidden
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className="pointer-events-none absolute inset-2 rounded-lg border border-dashed border-signal/45"
            />
          )}
        </AnimatePresence>

        <div className="relative p-5 sm:p-6">
          {/* --- Headline microcopy --- */}
          <div className="mb-4">
            <h2 className="text-lg font-light tracking-tight text-text sm:text-xl">
              {t('input.dropAnything')}
            </h2>
            <p className="mt-1.5 text-sm leading-relaxed text-text-dim">
              {t('input.sub')}
            </p>
          </div>

          {/* --- Captured signal preview --- */}
          <AnimatePresence mode="wait">
            {hasSignal ? (
              <motion.div
                key="signal"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
                className="flex items-center gap-3.5 rounded-lg border border-line bg-surface-inset/70 p-3.5"
              >
                {signal?.previewUrl ? (
                  <img
                    src={signal.previewUrl}
                    alt={t('input.imagePreviewAlt')}
                    className="size-12 shrink-0 rounded-md border border-line object-cover"
                  />
                ) : signal?.kind === 'file' ? (
                  // A text file has no preview. A generic document
                  // glyph is honest here; rendering a broken image
                  // placeholder would imply a decode failure.
                  <span className="flex size-12 shrink-0 items-center justify-center rounded-md border border-line bg-surface">
                    <FileText size={16} className="text-text-dim" />
                  </span>
                ) : (
                  <span className="flex size-12 shrink-0 items-center justify-center rounded-md border border-line bg-surface">
                    <Link2 size={16} className="text-signal/80" />
                  </span>
                )}

                <div className="min-w-0 flex-1">
                  <p className="mono-label text-signal/80">
                    {signal?.kind === 'url'
                      ? t('input.receivedUrl')
                      : signal?.kind === 'screenshot'
                        ? t('input.receivedScreenshot')
                        : signal?.kind === 'file'
                          ? t('input.receivedFile')
                          : signal?.kind === 'qr'
                            ? t('input.receivedQr')
                            : t('input.receivedImage')}
                  </p>
                  <p className="ltr-embed mt-1 truncate text-xs text-text-muted">
                    {signal?.label}
                  </p>
                </div>

                {isResult && (
                  <button
                    type="button"
                    onClick={onReset}
                    aria-label={t('actions.reset')}
                    className="shrink-0 rounded-full border border-line p-2 text-text-dim transition-colors hover:border-line-bright hover:text-text"
                  >
                    <X size={14} />
                  </button>
                )}
              </motion.div>
            ) : (
              <motion.div
                key="entry"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.3 }}
                className="flex flex-col gap-3"
              >
                {/* Hidden file picker: shared by drop, clipboard and button */}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept={ACCEPTED[modality]}
                  className="sr-only"
                  onChange={(event) => {
                    const file = event.target.files?.[0]
                    if (file) acceptFile(file)
                    // Reset so re-selecting the same file still fires change.
                    event.target.value = ''
                  }}
                />

                {/* Order IS the hierarchy: an upload mode renders its
                    affordance first and carries the emphasised border;
                    URL is deliberately quieter, because it is the
                    secondary modality. */}
                {isUrlMode ? (
                  <>
                    {urlAffordance}
                    {uploadAffordance}
                  </>
                ) : (
                  <>
                    {uploadAffordance}
                    {urlAffordance}
                  </>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {/* --- Footer hints --- */}
          <div className="mt-3.5 flex flex-wrap items-center justify-between gap-2">
            <p className="text-[0.7rem] leading-relaxed text-text-dim/80">
              {t('input.clipboardHint')}
            </p>
            {!hasSignal && (
              <button
                type="button"
                onClick={loadExample}
                className="text-[0.7rem] text-signal/70 underline-offset-4 transition-colors hover:text-signal hover:underline"
              >
                {t('actions.exampleUrl')}
              </button>
            )}
          </div>
        </div>
      </motion.div>
    </div>
  )
}
