/**
 * Capability registry for the Capabilities and Dashboard sections.
 *
 * Grouping is by real state, not by marketing tier: what analyses
 * something today, what is partial, and what is still on the
 * roadmap. No entry carries a metric, because no metric has been
 * measured outside the project's own held-out evaluation — see
 * `dashboard.honestyNoteBody`.
 *
 * Phase 3.7 note: OCR, QR, encoded content, file intelligence and
 * evidence fusion are now real. Several of these previously read
 * "planned" and analysed nothing; they were corrected rather than
 * left aspirational, because a roadmap entry that has shipped is a
 * false statement about the platform.
 *
 * The `limited` state is its own state for a reason: C2PA support
 * can find a manifest and attempt signature validation, but it is
 * not a full trust-list implementation. Neither "Active" nor
 * "Planned" describes it honestly.
 */

import type { TranslationKey } from '../i18n/translations'
import type { ModuleState } from './detectionCategories'

export interface Capability {
  id: string
  nameKey: TranslationKey
  bodyKey: TranslationKey
  state: ModuleState
  /** The primary modality leads every listing. */
  primary?: boolean
}

/** Analyses a signal end-to-end today. */
export const activeCapabilities: Capability[] = [
  {
    id: 'image-ensemble',
    nameKey: 'capabilities.imageIntelligence.name',
    bodyKey: 'capabilities.imageIntelligence.body',
    state: 'researchGrade',
    primary: true,
  },
  {
    id: 'url-intelligence',
    nameKey: 'capabilities.urlIntelligence.name',
    bodyKey: 'capabilities.urlIntelligence.body',
    state: 'advisory',
  },
  {
    id: 'evidence-fusion',
    nameKey: 'capabilities.evidenceFusion.name',
    bodyKey: 'capabilities.evidenceFusion.body',
    state: 'active',
  },
  {
    id: 'screenshot-ocr',
    nameKey: 'capabilities.screenshotOcr.name',
    bodyKey: 'capabilities.screenshotOcr.body',
    state: 'active',
  },
  {
    id: 'qr-extraction',
    nameKey: 'capabilities.qrExtraction.name',
    bodyKey: 'capabilities.qrExtraction.body',
    state: 'active',
  },
  {
    id: 'file-intelligence',
    nameKey: 'capabilities.fileIntelligence.name',
    bodyKey: 'capabilities.fileIntelligence.body',
    state: 'active',
  },
  {
    id: 'encoded-content',
    nameKey: 'capabilities.encodedContent.name',
    bodyKey: 'capabilities.encodedContent.body',
    state: 'active',
  },
  {
    id: 'provenance-forensics',
    nameKey: 'capabilities.provenance.name',
    bodyKey: 'capabilities.provenance.body',
    state: 'active',
  },
  {
    id: 'trust-dna',
    nameKey: 'capabilities.trustDna.name',
    bodyKey: 'capabilities.trustDna.body',
    state: 'active',
  },
  {
    id: 'evidence-graph',
    nameKey: 'capabilities.evidenceGraph.name',
    bodyKey: 'capabilities.evidenceGraph.body',
    state: 'active',
  },
  {
    id: 'timeline',
    nameKey: 'capabilities.timeline.name',
    bodyKey: 'capabilities.timeline.body',
    state: 'active',
  },
]

/**
 * Partially supported, and labelled as such wherever it is shown.
 *
 * A list of its own rather than a sub-flag on an active module,
 * because "limited" is a different claim from "active" and burying
 * it in a tooltip is how a reader ends up over-trusting it.
 */
export const limitedCapabilities: Capability[] = [
  {
    id: 'c2pa',
    nameKey: 'capabilities.c2pa.name',
    bodyKey: 'capabilities.c2pa.body',
    state: 'limited',
  },
]

/** Announced, not yet analysable. */
export const plannedCapabilities: Capability[] = [
  {
    id: 'correlation',
    nameKey: 'capabilities.correlation.name',
    bodyKey: 'capabilities.correlation.body',
    state: 'inDevelopment',
  },
]

/** Platform Status rows, exactly as the Dashboard reports them. */
export const platformStatus: { nameKey: TranslationKey; state: ModuleState }[] = [
  { nameKey: 'capabilities.imageIntelligence.name', state: 'researchGrade' },
  { nameKey: 'capabilities.urlIntelligence.name', state: 'advisory' },
  { nameKey: 'capabilities.evidenceFusion.name', state: 'active' },
  { nameKey: 'capabilities.screenshotOcr.name', state: 'active' },
  { nameKey: 'capabilities.qrExtraction.name', state: 'active' },
  { nameKey: 'capabilities.encodedContent.name', state: 'active' },
  { nameKey: 'capabilities.fileIntelligence.name', state: 'active' },
  { nameKey: 'capabilities.c2pa.name', state: 'limited' },
  { nameKey: 'capabilities.correlation.name', state: 'inDevelopment' },
]
