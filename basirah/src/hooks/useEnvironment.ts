import { useCallback, useSyncExternalStore } from 'react'

/* ============================================================
   Environment capability hooks.

   These read browser state through useSyncExternalStore rather than
   useState+useEffect: the value is external, it must never trigger a
   render-phase update, and the store pattern guarantees tear-free
   reads across concurrent renders.
   ============================================================ */

function subscribeToMedia(query: string) {
  return (onChange: () => void) => {
    const mql = window.matchMedia(query)
    mql.addEventListener('change', onChange)
    return () => mql.removeEventListener('change', onChange)
  }
}

/** true when the user has asked the OS to reduce motion. */
export function usePrefersReducedMotion(): boolean {
  return useSyncExternalStore(
    subscribeToMedia('(prefers-reduced-motion: reduce)'),
    () => window.matchMedia('(prefers-reduced-motion: reduce)').matches,
    () => false,
  )
}

/** True on devices with a coarse pointer (touch-first). */
export function useIsTouchDevice(): boolean {
  return useSyncExternalStore(
    subscribeToMedia('(hover: none), (pointer: coarse)'),
    () => window.matchMedia('(hover: none), (pointer: coarse)').matches,
    () => false,
  )
}

/** Below the `md` breakpoint — used to lighten animation budgets. */
export function useIsCompactViewport(): boolean {
  return useSyncExternalStore(
    subscribeToMedia('(max-width: 767px)'),
    () => window.matchMedia('(max-width: 767px)').matches,
    () => false,
  )
}

/**
 * Resolves true when expensive ambience should run: a desktop-class
 * viewport, a fine pointer, and no reduced-motion preference.
 */
export function useRichMotion(): boolean {
  const reduced = usePrefersReducedMotion()
  const touch = useIsTouchDevice()
  const compact = useIsCompactViewport()
  return !reduced && !touch && !compact
}

/**
 * Element-ref based drag-and-drop. Kept separate from the input
 * component so the same drop target logic can back the Intelligence Core
 * and the paste field.
 */
export interface DragZoneHandlers {
  onDragEnter: (event: React.DragEvent) => void
  onDragOver: (event: React.DragEvent) => void
  onDragLeave: (event: React.DragEvent) => void
  onDrop: (event: React.DragEvent) => void
  onPaste: (event: React.ClipboardEvent) => void
}

export function useDragZone(
  onFile: (file: File) => void,
  onDragStateChange: (dragging: boolean) => void,
): DragZoneHandlers {
  const handleDragEnter = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault()
      onDragStateChange(true)
    },
    [onDragStateChange],
  )

  const handleDragOver = useCallback((event: React.DragEvent) => {
    // Without preventDefault the browser navigates to the dropped file
    // and the SPA is destroyed.
    event.preventDefault()
    event.dataTransfer.dropEffect = 'copy'
  }, [])

  const handleDragLeave = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault()
      // relatedTarget is null when the pointer leaves the window; only a
      // genuine move to a descendant should keep the drag state alive.
      if (event.currentTarget.contains(event.relatedTarget as Node | null)) return
      onDragStateChange(false)
    },
    [onDragStateChange],
  )

  const handleDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault()
      onDragStateChange(false)
      const file = event.dataTransfer.files?.[0]
      if (file) onFile(file)
    },
    [onFile, onDragStateChange],
  )

  const handlePaste = useCallback(
    (event: React.ClipboardEvent) => {
      const items = event.clipboardData?.items
      if (!items) return
      for (const item of Array.from(items)) {
        if (item.kind === 'file' && item.type.startsWith('image/')) {
          const file = item.getAsFile()
          if (file) {
            event.preventDefault()
            onFile(file)
            return
          }
        }
      }
    },
    [onFile],
  )

  return {
    onDragEnter: handleDragEnter,
    onDragOver: handleDragOver,
    onDragLeave: handleDragLeave,
    onDrop: handleDrop,
    onPaste: handlePaste,
  }
}
