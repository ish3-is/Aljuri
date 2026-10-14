/** Evidence filters for Phase 4.

Classifies evidence by category: Verified, Model, Heuristic, Risk, Trust, Conflict, Unavailable.
*/
import type { EvidenceNode } from '../types/analysis';

export type FilterKind = 'verified' | 'model' | 'heuristic' | 'risk' | 'trust' | 'conflict' | 'unavailable';

export interface EvidenceFilter {
  kind: FilterKind;
  label: string;
  description: string;
}

export const EVIDENCE_FILTERS: EvidenceFilter[] = [
  { kind: 'verified', label: 'Verified', description: 'Cross-checked against independent sources.' },
  { kind: 'model', label: 'Model', description: 'Output of a trained model or heuristic engine.' },
  { kind: 'heuristic', label: 'Heuristic', description: 'Pattern-based signal, not a trained model.' },
  { kind: 'risk', label: 'Risk', description: 'Indicates elevated risk or high-risk destination.' },
  { kind: 'trust', label: 'Trust', description: 'Supports trust assessment.' },
  { kind: 'conflict', label: 'Conflict', description: 'Cross-modal disagreement detected.' },
  { kind: 'unavailable', label: 'Unavailable', description: 'Evidence could not be established.' },
];

/** Classify a node by filter category. */
export function classifyNodeForFilter(node: EvidenceNode): FilterKind | null {
  if (node.polarity === 'risk' || node.polarity === 'neutral') return 'risk';
  if (node.polarity === 'trust') return 'trust';
  if (node.weight === 'primary') return 'verified';
  return null;
}
