/* ============================================================
   BLIND DEFENCE TEST — measured results

   These numbers are NOT invented and NOT rounded by this file.
   Every value below is a verbatim transcription of
   `backend/results/phase37/blind_defense_test.json`, the project's
   own held-out evaluation run. They are embedded rather than
   fetched so the panel renders identically with the backend down,
   and because a metrics panel that silently disappears when a
   service is unreachable is worse than one that always renders.

   WHAT IS AND IS NOT SHOWN:

   Shown — the eight figures the evaluation actually produced, and
   only those. Every other statistic in the JSON (detection rate,
   coverage, per-family breakdowns) is deliberately omitted,
   because most of them describe a class this platform cannot
   measure. Coverage in particular would read as "31% of the time
   it got it right", which is a category error: an abstention is a
   refusal to decide, not a wrong answer.

   Limitations travel WITH the figures. Four are stated on the
   panel itself, because a 0/26 false-authentic rate reads as
   near-perfection until you learn that n is 26 synthetic images of
   an unknown generator family and the real class is a captioning
   dataset.

   The mandatory note is exact and must not be paraphrased:
   "This evaluation is a controlled defense set and does not
   represent universal real-world accuracy."
   ============================================================ */

/** The panel's figures. Field names mirror the source JSON. */
export interface BlindTestResult {
  /** total images in the defence set */
  sampleCount: number
  /** how many were synthetic */
  syntheticCount: number
  /** how many were real */
  realCount: number

  /** ensemble "authentic" calls on synthetic images, of 26 */
  falseAuthenticCount: number
  falseAuthenticDenominator: number

  /** Detector A's false-authentic calls, of the same 26 */
  detectorAFalseAuthentic: number
  detectorBFalseAuthentic: number
  detectorDenominator: number

  /** samples where the two detectors landed on opposite sides */
  disagreements: number

  /** share of samples on which the system declined to decide */
  abstentionRate: number

  /** samples the models had not been validated on */
  outOfDistribution: number

  /** mean wall-clock analysis time per sample, milliseconds */
  meanLatencyMs: number
}

/**
 * Verbatim from `results/phase37/blind_defense_test.json`.
 *
 * Source of every field:
 *   overall.n                               -> sampleCount
 *   overall.n_synthetic / n_real            -> syntheticCount / realCount
 *   overall.false_authentic_count (of 26)   -> falseAuthenticCount
 *   per_detector_false_authentic.detector_a.false_authentic_count
 *   per_detector_false_authentic.detector_b.false_authentic_count
 *   detector_disagreements                  -> disagreements
 *   overall.abstention_rate                 -> abstentionRate
 *   distribution_status_counts.out_of_distribution
 *   mean_duration_ms                        -> meanLatencyMs
 */
export const blindDefenseTest: BlindTestResult = {
  sampleCount: 51,
  syntheticCount: 26,
  realCount: 25,
  falseAuthenticCount: 0,
  falseAuthenticDenominator: 26,
  detectorAFalseAuthentic: 7,
  detectorBFalseAuthentic: 0,
  detectorDenominator: 26,
  disagreements: 9,
  abstentionRate: 0.1961,
  outOfDistribution: 1,
  meanLatencyMs: 203.3,
}

/**
 * The mandatory caveat, in English.
 *
 * Exported as a constant rather than left in the translation tree
 * because it is a statement ABOUT the evaluation whose wording is
 * fixed by that evaluation's own documentation. Translating it is
 * fine; re-wording it is not.
 */
export const BLIND_TEST_CAVEAT =
  'This evaluation is a controlled defense set and does not represent universal real-world accuracy.'