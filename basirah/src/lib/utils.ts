/** Small shared class-name helper. */
export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(' ')
}

/** Clamp a number into an inclusive range. */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

/** Map a 0-100 score onto a classification band. */
export function scoreToRisk(score: number): 'trusted' | 'caution' | 'high_risk' {
  if (score >= 70) return 'trusted'
  if (score >= 45) return 'caution'
  return 'high_risk'
}

/**
 * Format a duration as a forensic clock offset (mm:ss.mmm).
 * Used by the investigation timeline so records look like captured evidence.
 */
export function formatOffset(seconds: number): string {
  const mm = Math.floor(seconds / 60)
  const ss = Math.floor(seconds % 60)
  const ms = Math.floor((seconds % 1) * 1000)
  return `${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}.${String(
    ms,
  ).padStart(3, '0')}`
}

/**
 * Western digits are used for numerals and scores in BOTH languages.
 * Scores read as measured evidence, and mixed digit systems inside one
 * Arabic report make figures ambiguous. Arabic-Indic digits remain
 * available in the mock copy where editorial tone matters.
 */
export function formatScore(value: number): string {
  return String(Math.round(value)).padStart(2, '0')
}

/** Detect a plausible URL in free text. */
export function looksLikeUrl(value: string): boolean {
  const trimmed = value.trim()
  if (!trimmed || /\s/.test(trimmed)) return false
  const candidate = /^[a-z][a-z0-9+.-]*:\/\//i.test(trimmed)
    ? trimmed
    : `https://${trimmed}`
  try {
    const url = new URL(candidate)
    // Require a dot-separated host with a plausible TLD length, so plain
    // words ("login") are not mistaken for a domain.
    return /^[^.]+\.[a-z]{2,}$/i.test(url.hostname)
  } catch {
    return false
  }
}
