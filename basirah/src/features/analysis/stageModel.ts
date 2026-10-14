import type { AnalysisLane, TimelineStageId } from '../../types/analysis'
import type { TranslationKey } from '../../i18n/translations'

/**
 * The canonical stage order for an investigation.
 *
 * `useInvestigation` walks (a filtered subset of) this list to pace the
 * simulated run, so the journey, the timeline and the lane fills all
 * derive their progress from one source rather than three counters that
 * can disagree.
 */
export const STAGE_ORDER: TimelineStageId[] = [
  'acquire',
  'identify',
  'visual',
  'url',
  'metadata',
  'provenance',
  'synthetic',
  'correlate',
  'score',
]

/** Which analysis lane a stage belongs to. Drives the lane panel fills. */
export const STAGE_LANE: Record<TimelineStageId, AnalysisLane | 'fusion' | 'ingest'> = {
  acquire: 'ingest',
  identify: 'identity',
  visual: 'synthetic_media',
  url: 'url_intelligence',
  metadata: 'metadata',
  provenance: 'provenance',
  synthetic: 'synthetic_media',
  correlate: 'fusion',
  score: 'fusion',
}

/** The five lanes shown as parallel branches below INPUT. */
export const ANALYSIS_LANES: AnalysisLane[] = [
  'url_intelligence',
  'synthetic_media',
  'metadata',
  'provenance',
  'identity',
]

/** i18n keys, kept beside the topology so labels and lanes stay in sync. */
export const LANE_LABEL_KEY: Record<AnalysisLane, TranslationKey> = {
  url_intelligence: 'journey.lanes.urlIntel',
  synthetic_media: 'journey.lanes.syntheticMedia',
  metadata: 'journey.lanes.metadata',
  provenance: 'journey.lanes.provenance',
  identity: 'journey.lanes.identity',
  fusion: 'journey.lanes.fusion',
}

export const STAGE_LABEL_KEY: Record<TimelineStageId, TranslationKey> = {
  acquire: 'journey.stages.acquire',
  identify: 'journey.stages.identify',
  visual: 'journey.stages.visual',
  url: 'journey.stages.url',
  metadata: 'journey.stages.metadata',
  provenance: 'journey.stages.provenance',
  synthetic: 'journey.stages.synthetic',
  correlate: 'journey.stages.correlate',
  score: 'journey.stages.score',
}
