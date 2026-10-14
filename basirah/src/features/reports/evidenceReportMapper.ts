import type { AnalysisResult, EvidenceDetail } from '../../types/analysis'
import type { ReportClaim, ReportClaimKind } from '../../types/report'

/* ============================================================
   MODALITY MAPPERS -> REPORT CLAIMS

   One mapper per modality, each producing the same four-bucket
   claim list. The point of the split is that a reader can tell,
   section by section, which lines are measurements and which are
   model opinions — without the report itself having to hedge every
   sentence in prose.

   The buckets, and what may go in each:

     verifiedFact      a measurement or an observation. "No valid C2PA
                       manifest was found." True whether or not a
                       model ran.
     modelInference    a probabilistic conclusion. "Detector B
                       indicates synthetic characteristics."
     heuristicSignal   a weak structural indicator. Supports, never
                       decides.
     unavailableEvidence   what could not be established. The absence
                       of provenance, the absence of a decoded QR,
                       an abstention. Stated as plainly as a positive
                       finding, because a report that lists only what
                       it found implies the rest was clean.

   NOTHING is invented here. Every claim is derived from a field the
   backend actually returned, and a claim is only emitted when the
   field is present — an absent measurement produces a line in
   `unavailableEvidence` or no line at all, never a placeholder.
   ============================================================ */

/** Localised pairs used across the mappers. */
interface Wording {
  /** Detector named as indicating synthetic characteristics. */
  detectorInfers: (name: string) => [string, string]
  /** An abstention, as an unavailable-evidence line. */
  abstained: (reasons: string) => [string, string]
}

const WORDING: Wording = {
  detectorInfers: (name) => [
    `${name} indicates synthetic characteristics.`,
    `يشير ${name} إلى خصائص اصطناعية.`,
  ],
  abstained: (reasons) => [
    `The detectors abstained rather than deciding (${reasons}). No combined likelihood is published.`,
    `امتنع الكاشفان عن الحسم (${reasons}) ولم يُنشر احتمال مجمع.`,
  ],
}

/** Build one claim with a single wording source (English both sides). */
function claim(
  kind: ReportClaimKind,
  id: string,
  source: string,
  labelEn: string,
  labelAr: string,
  detailEn: string,
  detailAr: string,
): ReportClaim {
  return { id, kind, source, labelEn, labelAr, detailEn, detailAr }
}

/* ------------------------------------------------------------------ */
/* Shared: provenance                                                  */
/* ------------------------------------------------------------------ */

/**
 * Provenance splits across three buckets, because its three facts
 * have genuinely different epistemic weight:
 *
 *   verifiedFact        "No valid C2PA manifest was found."
 *   unavailableEvidence "Publicly trusted provenance could not be
 *                       established." — because until credentials
 *                       verify, provenance is an open question, and
 *                       an open question must be reported as one.
 *
 * `modelInference` is deliberately NOT used here even when a
 * manifest asserts generative creation: an assertion inside a
 * credential is a measured fact about the credential, and the report
 * says exactly that rather than promoting it to a conclusion.
 */
function provenanceClaims(detail: EvidenceDetail): ReportClaim[] {
  const prov = detail.provenance
  if (!prov) return []

  const claims: ReportClaim[] = []

  if (prov.status === 'unavailable') {
    claims.push(
      claim(
        'verifiedFact',
        'prov-absent',
        'c2pa',
        'Provenance',
        'المصدر',
        'No valid C2PA manifest was found.',
        'لم يُعثر على بيان C2PA صالح.',
      ),
      claim(
        'unavailableEvidence',
        'prov-unestablished',
        'c2pa',
        'Provenance',
        'المصدر',
        'Publicly trusted provenance could not be established. The absence of Content Credentials does not prove that the content is authentic or synthetic.',
        'تعذّر إثبات مصدر موثوق علناً. وغياب بيانات الاعتماد لا يثبت أن المحتوى أصلي أو اصطناعي.',
      ),
    )
    return claims
  }

  claims.push(
    claim(
      'verifiedFact',
      'prov-status',
      'c2pa',
      'Provenance',
      'المصدر',
      // `null` is reported as "not validated", which is a different
      // claim from "not verified": nothing existed to validate.
      `Content Credentials status: ${prov.status}. Manifest present: ${prov.manifestPresent ? 'yes' : 'no'}. Signature ${prov.signatureVerified === null ? 'not validated (no manifest present)' : prov.signatureVerified ? 'verified' : 'not verified'}.`,
      `حالة بيانات الاعتماد: ${prov.status}. البيان موجود: ${prov.manifestPresent ? 'نعم' : 'لا'}. التوقيع ${prov.signatureVerified === null ? 'غير محقَّق (لا بيان موجود)' : prov.signatureVerified ? 'موثَّق' : 'غير موثَّق'}.`,
    ),
  )

  // The assertion is a fact ABOUT the credential. It becomes a
  // conclusion only when the signature verified, and even then the
  // report phrases it as what the credential asserts.
  if (prov.signatureVerified && prov.aiGeneratedAssertion) {
    claims.push(
      claim(
        'verifiedFact',
        'prov-ai-assertion',
        'c2pa',
        'Credential assertion',
        'إقرار بيانات الاعتماد',
        'Verified credentials assert generative creation.',
        'تُقرّ بيانات الاعتماد الموثَّقة بأن المحتوى مُولَّد.',
      ),
    )
  } else if (prov.aiGeneratedAssertion !== null) {
    claims.push(
      claim(
        'verifiedFact',
        'prov-ai-assertion-weak',
        'c2pa',
        'Credential assertion',
        'إقرار بيانات الاعتماد',
        prov.signatureVerified
          ? 'Verified credentials do not assert generative creation.'
          : 'An unverified credential carries an AI-generation assertion that was not signature-validated.',
        prov.signatureVerified
          ? 'لا تُقرّ بيانات الاعتماد الموثَّقة بأن المحتوى مُولَّد.'
          : 'تحمل بيانات اعتماد غير موثَّقة إقرار توليد بالذكاء الاصطناعي لم يجرِ التحقق من توقيعه.',
      ),
    )
  }

  if (prov.status === 'present_unverified') {
    claims.push(
      claim(
        'unavailableEvidence',
        'prov-not-verified',
        'c2pa',
        'Credential trust',
        'ثقة بيانات الاعتماد',
        'A manifest was present but its signature was not validated, so it supports no conclusion.',
        'كان البيان موجوداً لكن لم يُتحقق من توقيعه، لذلك لا يدعم أي استنتاج.',
      ),
    )
  }

  return claims
}

/* ------------------------------------------------------------------ */
/* Shared: detector ensemble                                           */
/* ------------------------------------------------------------------ */

/**
 * The ensemble's claims.
 *
 * The critical rule lives here: on conflict, each detector is
 * reported as its OWN inference and the ensemble contributes only an
 * `unavailableEvidence` line. No combined likelihood is ever emitted,
 * because there is none to report — a mean of two opposing opinions
 * is a number the backend deliberately did not publish.
 */
function ensembleClaims(detail: EvidenceDetail): ReportClaim[] {
  const ens = detail.ensemble
  if (!ens) return []

  const claims: ReportClaim[] = []
  const conflict = ens.detectorAgreement === 'conflict'

  // Each detector, separately, always.
  for (const detector of ens.detectors) {
    if (detector.status !== 'available') {
      claims.push(
        claim(
          'unavailableEvidence',
          `detector-${detector.modelName}-unavailable`,
          'ensemble',
          detector.modelName,
          detector.modelName,
          `The detector did not run: ${detector.unavailableReason ?? 'no reason supplied'}.`,
          `لم يعمل الكاشف: ${detector.unavailableReason ?? 'بلا سبب مذكور'}.`,
        ),
      )
      continue
    }

    const [infersEn, infersAr] = WORDING.detectorInfers(detector.modelName)
    claims.push(
      claim(
        'modelInference',
        `detector-${detector.modelName}`,
        'ensemble',
        detector.modelName,
        detector.modelName,
        detector.syntheticProbability >= 0.5
          ? `${infersEn} This detector's own synthetic likelihood is ${(detector.syntheticProbability * 100).toFixed(1)}%.`
          : `This detector found no strong synthetic indication of its own (synthetic likelihood ${(detector.syntheticProbability * 100).toFixed(1)}%). It does not assert that the content is authentic.`,
        detector.syntheticProbability >= 0.5
          ? `${infersAr} احتمال هذا الكاشف الخاص بالاصطناع ${(detector.syntheticProbability * 100).toFixed(1)}٪.`
          : `لم يجد هذا الكاشف مؤشر اصطناعي قوياً خاصاً به (احتمال اصطناع ${(detector.syntheticProbability * 100).toFixed(1)}٪)، وهو لا يُقرّ بأن المحتوى أصلي.`,
      ),
    )
  }

  // Agreement itself is a measured fact about the two models.
  claims.push(
    claim(
      'verifiedFact',
      'ensemble-agreement',
      'ensemble',
      'Detector agreement',
      'توافق الكاشفين',
      `Detector agreement: ${ens.detectorAgreement}. Evidence quality: ${ens.evidenceQuality}. Distribution: ${ens.distributionStatus}.`,
      `توافق الكاشفين: ${ens.detectorAgreement}. جودة الأدلة: ${ens.evidenceQuality}. التوزيع: ${ens.distributionStatus}.`,
    ),
  )

  if (conflict) {
    const [abstainEn, abstainAr] = WORDING.abstained(
      ens.abstentionReasons.join(', ') || 'detector_disagreement',
    )
    claims.push(
      claim(
        'unavailableEvidence',
        'ensemble-conflict',
        'ensemble',
        'Detector conflict',
        'تعارض الكاشفين',
        `The two detectors reached opposite conclusions. ${abstainEn}`,
        `وصل الكاشفان إلى نتيجتين متعاكستين. ${abstainAr}`,
      ),
    )
    return claims
  }

  if (ens.abstained) {
    const [abstainEn, abstainAr] = WORDING.abstained(ens.abstentionReasons.join(', '))
    claims.push(
      claim(
        'unavailableEvidence',
        'ensemble-abstained',
        'ensemble',
        'Abstention',
        'الامتناع',
        abstainEn,
        abstainAr,
      ),
    )
  }

  if (ens.syntheticLikelihood !== null) {
    claims.push(
      claim(
        'modelInference',
        'ensemble-likelihood',
        'ensemble',
        'Synthetic likelihood',
        'احتمال الاصطناع',
        `The combined synthetic likelihood is ${(ens.syntheticLikelihood * 100).toFixed(1)}%. This is a probabilistic output, not a verdict.`,
        `الاحتمال المجمع للاصطناع ${(ens.syntheticLikelihood * 100).toFixed(1)}٪. هذا مخرَج احتمالي لا حكم.`,
      ),
    )
  }

  if (ens.distributionStatus === 'out_of_distribution') {
    claims.push(
      claim(
        'unavailableEvidence',
        'ensemble-ood',
        'ensemble',
        'Distribution',
        'التوزيع',
        'The content is out of distribution, so detector evidence carries less weight: the models were not validated on material like this.',
        'المحتوى خارج نطاق التوزيع، لذلك يحمل دليل الكاشفين وزناً أقل: فالنماذج لم تُتحقق على مادة كهذه.',
      ),
    )
  }

  return claims
}

/* ------------------------------------------------------------------ */
/* Shared: OCR / QR / URL / encoding                                   */
/* ------------------------------------------------------------------ */

function contentClaims(detail: EvidenceDetail): ReportClaim[] {
  const claims: ReportClaim[] = []

  // ---- OCR ----
  if (detail.ocr) {
    const engines = detail.ocr.enginesUsed.length > 0
      ? detail.ocr.enginesUsed.join(', ')
      : detail.ocr.engine
    claims.push(
      claim(
        'verifiedFact',
        'ocr-ran',
        'ocr',
        'OCR',
        'التعرّف الضوئي',
        `OCR ran with: ${engines}. Confidence ${detail.ocr.confidence === null ? 'not reported' : detail.ocr.confidence.toFixed(2)}. Arabic detected: ${detail.ocr.containsArabic ? 'yes' : 'no'}.`,
        `عمل التعرّف الضوئي عبر: ${engines}. الثقة ${detail.ocr.confidence === null ? 'غير مذكورة' : detail.ocr.confidence.toFixed(2)}. رصد العربية: ${detail.ocr.containsArabic ? 'نعم' : 'لا'}.`,
      ),
    )
    if (!detail.ocr.containsArabic) {
      claims.push(
        claim(
          'unavailableEvidence',
          'ocr-no-arabic',
          'ocr',
          'Arabic text',
          'النص العربي',
          'No Arabic text was extracted. Arabic OCR is available but weaker than English, particularly on small or low-contrast type, so this absence may reflect the engine rather than the content.',
          'لم يُستخرج نص عربي. التعرّف العربي متاح لكنه أضعف من الإنجليزية، خاصة مع خط صغير أو تباين منخفض، فقد يعكس هذا الغياب المحرك لا المحتوى.',
        ),
      )
    }
  }

  // ---- QR ----
  if (detail.qr) {
    if (detail.qr.payload) {
      claims.push(
        claim(
          'verifiedFact',
          'qr-payload',
          'qr',
          'QR payload',
          'محتوى رمز QR',
          `A QR symbol was decoded (${detail.qr.decodeStatus}). Payload: ${detail.qr.payload}`,
          `فُك رمز استجابة سريعة (${detail.qr.decodeStatus}). المحتوى: ${detail.qr.payload}`,
        ),
      )
    } else {
      claims.push(
        claim(
          'verifiedFact',
          'qr-none',
          'qr',
          'QR',
          'رمز QR',
          'No QR symbol was found in this content.',
          'لم يُعثر على رمز استجابة سريعة في هذا المحتوى.',
        ),
      )
    }
  }

  // ---- URLs ----
  for (const [index, url] of detail.urls.entries()) {
    const highRisk = url.urlIntelligence.riskLevel === 'high_risk'
    if (!url.urlIntelligence.available) {
      claims.push(
        claim(
          'unavailableEvidence',
          `url-${index}-unavailable`,
          'url_intelligence',
          'URL intelligence',
          'استخبارات الروابط',
          `URL intelligence was unavailable for one candidate (${url.urlIntelligence.reason ?? 'no reason supplied'}).`,
          `لم تتوفر استخبارات الروابط لأحد المرشحين (${url.urlIntelligence.reason ?? 'بلا سبب مذكور'}).`,
        ),
      )
      continue
    }

    claims.push(
      claim(
        highRisk ? 'modelInference' : 'verifiedFact',
        `url-${index}`,
        'url_intelligence',
        'URL candidate',
        'مرشّح رابط',
        `A destination found via ${url.origin} was scored as high risk by URL Intelligence. It was not fetched, resolved or opened.`,
        `وجهة رُصدت عبر ${url.origin} قيّمتها استخبارات الروابط على أنها عالية الخطورة. ولم يُجلب رابطها ولا حُلّ ولا فُتح.`,
      ),
    )
  }

  // ---- Encoding ----
  for (const [index, finding] of detail.encoding.entries()) {
    claims.push(
      claim(
        'heuristicSignal',
        `encoding-${index}`,
        'encoded_content',
        finding.encodingType,
        finding.encodingType,
        `Encoded content of type ${finding.encodingType} was found (confidence ${finding.confidence.toFixed(2)}, depth ${finding.depth}). Decoded preview: ${finding.decodedPreview}`,
        `رُصد محتوى مشفّر من نوع ${finding.encodingType} (ثقة ${finding.confidence.toFixed(2)}، عمق ${finding.depth}). المعاينة المفكوكة: ${finding.decodedPreview}`,
      ),
    )
    if (finding.riskIndicators.length > 0) {
      claims.push(
        claim(
          'heuristicSignal',
          `encoding-${index}-risk`,
          'encoded_content',
          'Encoding risk indicators',
          'مؤشرات خطورة الترميز',
          `Risk indicators for the ${finding.encodingType} payload: ${finding.riskIndicators.join(', ')}.`,
          `مؤشرات خطورة الحمولة ${finding.encodingType}: ${finding.riskIndicators.join('، ')}.`,
        ),
      )
    }
  }

  return claims
}

/* ------------------------------------------------------------------ */
/* Modality mappers                                                    */
/* ------------------------------------------------------------------ */

/**
 * IMAGE claims.
 *
 * Detectors and provenance come from the shared mappers; this one
 * adds what is specific to a still image — forensic characteristics
 * and metadata, which are measurements, and the quality warnings
 * that bound how much the pixels can support at all.
 */
function imageClaims(detail: EvidenceDetail): ReportClaim[] {
  const claims: ReportClaim[] = [...provenanceClaims(detail), ...ensembleClaims(detail)]

  for (const [index, signal] of (detail.forensics ?? []).entries()) {
    const name = typeof signal.name === 'string' ? signal.name : `signal-${index}`
    const value = typeof signal.value === 'number' ? signal.value : null
    const meaning =
      typeof signal.meaningEn === 'string' ? signal.meaningEn : ''
    const doesNotMean =
      typeof signal.doesNotMeanEn === 'string' ? signal.doesNotMeanEn : ''

    claims.push(
      claim(
        'verifiedFact',
        `forensic-${index}`,
        'forensics',
        name.replace(/_/g, ' '),
        name.replace(/_/g, ' '),
        value === null
          ? `${name} was not measured.`
          : `${name}: ${value.toFixed(3)}. ${meaning} ${doesNotMean}`,
        value === null
          ? `لم تُقَس ${name}.`
          : `${name}: ${value.toFixed(3)}. ${meaning} ${doesNotMean}`,
      ),
    )
  }

  return claims
}

/**
 * SCREENSHOT claims.
 *
 * Everything an image produces, plus the content-reading channels.
 * The additional concern here is DIVERGENCE: a screenshot's pixels
 * and its on-screen links routinely disagree, so the fusion
 * explanation is preserved verbatim rather than reduced to the
 * single final word.
 */
function screenshotClaims(detail: EvidenceDetail): ReportClaim[] {
  return [...imageClaims(detail), ...contentClaims(detail)]
}

/**
 * FILE claims.
 *
 * A refused file produces ONLY `unavailableEvidence` and never a
 * positive fact. That asymmetry is deliberate: "we did not inspect
 * this" and "we inspected this and found nothing" must never render
 * the same way, and a refusal reported as a clean result is the most
 * dangerous thing this mapper could do.
 */
function fileClaims(detail: EvidenceDetail): ReportClaim[] {
  const claims: ReportClaim[] = []

  const file = detail.file
  if (!file) {
    claims.push(
      claim(
        'unavailableEvidence',
        'file-absent',
        'file_intelligence',
        'File intelligence',
        'ذكاء الملفات',
        'No file-intelligence block was produced for this upload.',
        'لم تُنتج كتلة ذكاء ملفات لهذا الرفع.',
      ),
    )
  } else if (!file.accepted) {
    claims.push(
      claim(
        'unavailableEvidence',
        'file-refused',
        'file_intelligence',
        'File refused',
        'رفض الملف',
        `The file was refused and was not analysed: ${file.reason ?? 'no reason supplied'}. Refusal is not a clean result; it means no measurement was taken.`,
        `رُفض الملف ولم يُحلَّل: ${file.reason ?? 'بلا سبب مذكور'}. والرفض ليس نتيجة نظيفة، بل يعني أنه لم يُؤخذ أي قياس.`,
      ),
    )
  } else {
    claims.push(
      claim(
        'verifiedFact',
        'file-accepted',
        'file_intelligence',
        'File type',
        'نوع الملف',
        `The file was accepted as ${file.fileKind} and ${file.textChars} characters of text were extracted.`,
        `قُبل الملف كـ ${file.fileKind} واستُخرج منه ${file.textChars} حرفاً من النص.`,
      ),
    )

    if (file.suspicious.length > 0) {
      claims.push(
        claim(
          'heuristicSignal',
          'file-suspicious',
          'file_intelligence',
          'Risk findings',
          'نتائج الخطورة',
          `Risk findings raised by file inspection: ${file.suspicious.join(', ')}.`,
          `نتائج خطورة رفعها فحص الملف: ${file.suspicious.join('، ')}.`,
        ),
      )
    }
  }

  // An accepted text file can still carry provenance-relevant bytes
  // and detector opinions only if it was an image, so the image
  // branches are NOT included here. URLs and encoding are.
  claims.push(...contentClaims(detail))

  return claims
}

/**
 * URL claims.
 *
 * A pasted URL never goes through the evidence endpoint, so this
 * mapper is fed the shared `AnalysisResult` contract instead. URL
 * structure and lexical signals are MEASUREMENTS of the string; the
 * risk band is the model's INFERENCE about them. Splitting them is
 * what stops "high risk" from reading like an observation about the
 * destination — which was never visited.
 */
function urlClaims(result: AnalysisResult): ReportClaim[] {
  const claims: ReportClaim[] = []

  claims.push(
    claim(
      'verifiedFact',
      'url-not-fetched',
      'url_intelligence',
      'Submission',
      'المُدخل',
      'The URL was analysed as a string. It was not fetched, resolved or opened.',
      'حُلّل الرابط كنص. ولم يُجلب ولا حُلّ ولا فُتح.',
    ),
  )

  for (const signal of result.secondarySignals) {
    claims.push(
      claim(
        'heuristicSignal',
        `url-signal-${signal.id}`,
        'url_intelligence',
        signal.metricKey,
        signal.metricKey,
        signal.valueEn,
        signal.valueAr,
      ),
    )
  }

  claims.push(
    claim(
      'modelInference',
      'url-band',
      'url_intelligence',
      'Risk band',
      'فئة الخطورة',
      `The URL engine placed this link in the ${result.riskLevel} band. This is a structural inference about the string, not a statement about what the destination does.`,
      `صنّف محلل الروابط هذا الرابط في فئة ${result.riskLevel}. هذا استنتاج بنيوي عن النص لا بيان عن ما تفعله الوجهة.`,
    ),
  )

  return claims
}

/* ------------------------------------------------------------------ */
/* Dispatcher                                                          */
/* ------------------------------------------------------------------ */

/**
 * Pick the right mapper for whichever payload this result carries.
 *
 * Dispatches on what the result ACTUALLY contains rather than on
 * what the user selected, so a screenshot submitted at the image
 * intake is reported with the screenshot channels it actually
 * produced.
 */
export function buildEvidenceClaims(result: AnalysisResult): ReportClaim[] {
  const detail = (result as { evidence?: EvidenceDetail }).evidence
  if (!detail) return urlClaims(result)

  /**
   * The RESOLVED modality, taken from the leading token.
   *
   * `detail.mode` can carry a backend annotation — e.g.
   * "image (requested 'screenshot' contradicted the content)" — so a
   * whole-string comparison would miss every documented mode and fall
   * through to the image mapper for a file upload.
   */
  const resolved = detail.mode.split(' ')[0]
  if (resolved === 'file') return fileClaims(detail)
  if (resolved === 'screenshot') return screenshotClaims(detail)

  // An image (or a mode the backend could not classify) is reported
  // with the image channels plus anything the content-reading
  // branches produced, since those can fire on an image too.
  return [...imageClaims(detail), ...contentClaims(detail)]
}

/** The fusion explanation, verbatim from the backend. */
export function fusionExplanation(result: AnalysisResult): {
  en: string
  ar: string
} {
  const detail = (result as { evidence?: EvidenceDetail }).evidence
  if (!detail) {
    return {
      en: 'This modality reports structural and lexical indicators only. It does not establish whether a link was visited, delivered or acted upon.',
      ar: 'تبلّغ هذه الوسيلة عن مؤشرات بنيوية ولفظية فقط، ولا تثبت ما إذا كان الرابط قد فُتح أو سلَّم أو حُول عليه إجراء.',
    }
  }
  return {
    en: detail.fusion.note,
    ar: detail.fusion.note,
  }
}

/** Limitations, with both languages already in the payload. */
export function reportLimitations(result: AnalysisResult): {
  en: string[]
  ar: string[]
} {
  const detail = (result as { evidence?: EvidenceDetail }).evidence
  if (detail) {
    return { en: detail.limitations, ar: detail.limitations }
  }
  return {
    en: [
      'This modality reports structural and lexical indicators only. It does not establish whether a link was visited, delivered or acted upon.',
    ],
    ar: [
      'تبلّغ هذه الوسيلة عن مؤشرات بنيوية ولفظية فقط، ولا تثبت ما إذا كان الرابط قد فُتح أو سلَّم أو حُول عليه إجراء.',
    ],
  }
}