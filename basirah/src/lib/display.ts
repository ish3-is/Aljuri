/** Confidence indicators for Phase 4.

Use Verified / Strong / Moderate / Weak / Uncertain - not misleading red/green percentages.
*/
export const CONFIDENCE_LEVELS = [
  { level: 'verified', label: 'Verified', description: 'High confidence; cross-checked against independent sources.' },
  { level: 'strong', label: 'Strong', description: 'High confidence; consistent with related evidence.' },
  { level: 'moderate', label: 'Moderate', description: 'Medium confidence; some uncertainty remains.' },
  { level: 'weak', label: 'Weak', description: 'Low confidence; treat as indicative only.' },
  { level: 'uncertain', label: 'Uncertain', description: 'No reliable conclusion; evidence is conflicting or missing.' },
];

export interface ConfidenceDisplay {
  label: string;
  description: string;
  color: string;
}

export function getConfidenceDisplay(level: string): ConfidenceDisplay {
  const mapping: Record<string, ConfidenceDisplay> = {
    verified: { label: 'Verified', description: 'High confidence; cross-checked against independent sources.', color: 'var(--color-trusted)' },
    strong: { label: 'Strong', description: 'High confidence; consistent with related evidence.', color: 'var(--color-signal)' },
    moderate: { label: 'Moderate', description: 'Medium confidence; some uncertainty remains.', color: 'var(--color-caution)' },
    weak: { label: 'Weak', description: 'Low confidence; treat as indicative only.', color: 'var(--color-danger)' },
    uncertain: { label: 'Uncertain', description: 'No reliable conclusion; evidence is conflicting or missing.', color: 'var(--color-line)' },
  };
  return mapping[level] || mapping.uncertain;
}
