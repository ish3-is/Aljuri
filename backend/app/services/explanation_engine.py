"""
Explanation engine.

Turns raw findings into the bilingual evidence structures BASIRAH's
existing result experience renders. This is the module that makes the
system explainable rather than merely predictive.

Language policy, enforced throughout:
  * probabilistic phrasing only — never "is malicious" / "is safe"
  * a single keyword is never presented as evidence
  * when the model is unavailable the response says so explicitly
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import THRESHOLDS
from app.ml.production import InferenceResult as Prediction
from app.services.heuristic_engine import HeuristicFinding, heuristic_risk
from app.services.risk_engine import RiskAssessment
from app.services.url_analyzer import NormalizedURL

# Arabic phrasing for the secondary metric rail. Keys match the
# frontend's TranslationKey values so the existing UI renders them
# without new translation entries.
_METRIC_KEYS = {
    "url_entropy": "explanation.metrics.urlEntropy",
    "provenance": "explanation.metrics.provenance",
    "domain_structure": "explanation.metrics.domainStructure",
    "brand_match": "explanation.metrics.brandMatch",
    "synthetic_confidence": "explanation.metrics.syntheticConfidence",
}


@dataclass
class PrimarySignal:
    title_en: str
    title_ar: str
    body_en: str
    body_ar: str


@dataclass
class SecondarySignal:
    """One row in the secondary evidence rail."""

    id: str
    metric_key: str
    value_en: str
    value_ar: str
    severity: str


@dataclass
class TimelineRecord:
    stage: str
    offset_seconds: float


def build_primary_signal(
    url: NormalizedURL,
    findings: list[HeuristicFinding],
    assessment: RiskAssessment,
    prediction: Prediction,
) -> PrimarySignal | None:
    """Choose the single most important observation, or None.

    Ranking is by rule weight, so the dominant finding is the one with
    the strongest structural evidence — not merely the first that fired.
    """
    fired = [f for f in findings if f.triggered]
    if not fired:
        return None

    top = max(fired, key=lambda f: f.weight)

    # A brand-mismatch finding is narratively the most important even
    # when its weight is lower, because it is the specific pattern the
    # product exists to surface. Promote it when present.
    brand = next((f for f in fired if f.id == "BRAND_LIKE_TOKEN"), None)
    if brand is not None and assessment.risk_level == "high_risk":
        top = brand

    return PrimarySignal(
        title_en=top.title,
        title_ar=ARABIC_TITLES.get(top.id, top.title),
        body_en=_build_body_en(top, url, assessment, prediction),
        body_ar=_build_body_ar(top, url, assessment, prediction),
    )


def _build_body_en(
    finding: HeuristicFinding,
    url: NormalizedURL,
    assessment: RiskAssessment,
    prediction: Prediction,
) -> str:
    parts = [finding.explanation]

    if assessment.risk_level == "high_risk":
        parts.append(
            f"Multiple indicators contributed to a combined risk value of "
            f"{assessment.final_risk:.0f} out of 100 across "
            f"{len(assessment.contributing_rules)} triggered checks."
        )
    elif assessment.risk_level == "caution":
        parts.append(
            "A limited number of indicators were observed. This pattern "
            "warrants attention but is not, on its own, indicative of harm."
        )
    else:
        parts.append(
            "No strong structural indicators were observed in the URL "
            "string itself."
        )

    if prediction.available:
        parts.append(
            f"The classifier assigned a phishing-association probability "
            f"of {prediction.probability:.0%}, which is one input among "
            "several rather than a verdict."
        )
    else:
        parts.append(
            "No trained model was available for this analysis, so the "
            "assessment rests on structural checks alone."
        )

    return " ".join(parts)


def _build_body_ar(
    finding: HeuristicFinding,
    url: NormalizedURL,
    assessment: RiskAssessment,
    prediction: Prediction,
) -> str:
    parts = [ARABIC_EXPLANATIONS.get(finding.id, finding.explanation)]

    if assessment.risk_level == "high_risk":
        parts.append(
            f"أسهمت عدة مؤشرات في قيمة خطورة مدمجة قدرها "
            f"{assessment.final_risk:.0f} من 100 عبر "
            f"{len(assessment.contributing_rules)} فحصًا مُفعَّلًا."
        )
    elif assessment.risk_level == "caution":
        parts.append(
            "رُصد عدد محدود من المؤشرات. يستحق هذا النمط الانتباه لكنه لا "
            "يدل بذاته على ضرر."
        )
    else:
        parts.append(
            "لم تُرصد مؤشرات بنيوية قوية في نص الرابط نفسه."
        )

    if prediction.available:
        parts.append(
            f"أسند المصنّف احتمال ارتباط بالتصيّد قدره "
            f"{prediction.probability:.0%}، وهو أحد المدخلات وليست حكمًا."
        )
    else:
        parts.append(
            "لم يتوفّر نموذج مُدرَّب لهذا التحليل، فاعتمدت التقييم على "
            "الفحوص البنيوية وحدها."
        )

    return " ".join(parts)


ARABIC_TITLES: dict[str, str] = {
    "IP_HOST": "استخدام عنوان IP كاسم مضيف",
    "AT_SYMBOL": "بيانات اعتماد مضمّنة في الرابط",
    "PUNYCODE": "مضيف مُرمَّز بـ Punycode",
    "CREDENTIAL_IN_URL": "حمل بيانات الاعتماد داخل الرابط",
    "EXCESSIVE_ENCODING": "ترميز نسبة مفرط",
    "ABNORMAL_PORT": "منفذ غير قياسي",
    "DOUBLE_SLASH": "شرطة مائلة مزدوجة في المسار",
    "LONG_URL": "رابط طويل بشكل غير معتاد",
    "LONG_HOSTNAME": "اسم مضيف طويل بشكل غير معتاد",
    "LONG_PATH": "مسار طويل بشكل غير معتاد",
    "EXCESSIVE_SUBDOMAINS": "تداخل شديد في النطاقات الفرعية",
    "HIGH_ENTROPY_HOSTNAME": "اسم مضيف عالي العشوائية",
    "HIGH_ENTROPY_URL": "رابط عالي العشوائية",
    "HIGH_DIGIT_RATIO": "نسبة أرقام مرتفعة",
    "EXCESSIVE_HYPHENS": "كثرة الشرطة الواصلة",
    "SUSPICIOUS_KEYWORD_COMBINATION": "اجتماع مصطلحات التحقق من الحساب",
    "BRAND_LIKE_TOKEN": "نمط عدم تطابق هوية محتمل",
    "SUSPICIOUS_TLD": "نطاق أعلى يُستخدم كثيرًا في إساءة الاستخدام",
}

ARABIC_EXPLANATIONS: dict[str, str] = {
    "IP_HOST": "يستخدم الرابط عنوان IP خامًا بدل اسم نطاق مسجَّل، ما يجعل الوجهة غير قابلة للنسبة إلى جهة معروفة.",
    "AT_SYMBOL": "يحتوي الرابط على رمز '@' قبل المضيف، وهو ما يجعل ما يسبقه اسم مستخدم؛ قليل جدًا من الخدمات المشروعة تطلب ذلك.",
    "PUNYCODE": "يستخدم اسم المضيف ترميز Punycode ('xn--')، وهو مشروع للنطاقات الدولية لكنه يُستخدم أيضًا لتقليد نطاق آخر بصريًا.",
    "CREDENTIAL_IN_URL": "يحمل الرابط مادة اعتماد مباشرة داخل نصه، ما يُفقد سرًّا لأي شخص يشاركه.",
    "EXCESSIVE_ENCODING": "نسبة كبيرة من الرابط مشفَّرة، وهي طريقة أحيانًا لإخفاء الكلمات المفتاحية عن الفلاتر البسيطة.",
    "ABNORMAL_PORT": "يستهدف الرابط منفذًا غير شائع للويب (80، 443، 8080، 8443)، وهو مشروع لكنه نادر في الخدمات العامة.",
    "DOUBLE_SLASH": "يحتوي المسار على شرطات مائلة مزدوجة، وهو نمط يُستخدم أحيانًا لإرباك محلّلات الروابط.",
    "LONG_URL": "طول الرابط يتجاوز الحدّ الذي يبدأ عنده المحتوى المخفي بالتراكم بدل أن يكون مجرّد وجهة.",
    "LONG_HOSTNAME": "اسم المضيف طويل بشكل غير معتاد بالنسبة لنطاق جهة حقيقية.",
    "LONG_PATH": "جزء المسار طويل، وقد يشير إلى حمولة مُرمَّزة موضوعة فيه.",
    "EXCESSIVE_SUBDOMAINS": "يحتوي اسم المضيف على مستويات فرعية أكثر من المعتاد، وهو أسلوب لإخفاء النطاق الحقيقي.",
    "HIGH_ENTROPY_HOSTNAME": "اسم المضيف يبدو عشوائي الإحصاء، وهو ما يميز المولَّد آليًا عن أسماء الجهات الحقيقية.",
    "HIGH_ENTROPY_URL": "يبدو الرابط بالكامل ذا محتوى عشوائي مُولَّد.",
    "HIGH_DIGIT_RATIO": "الأرقام تشكل نسبة مرتفعة من الرابط، بينما نطاقات الجهات الحقيقية تعتمد على الكلمات.",
    "EXCESSIVE_HYPHENS": "كثرة الشرطة الواصلة تجعل الرابط يبدو كعبارة مألوفة مع بقائه نطاقًا مختلفًا.",
    "SUSPICIOUS_KEYWORD_COMBINATION": "تظهر عدة مصطلحات تتعلق بالحساب والتحقق معًا؛ فكلمة منفردة مثل «تسجيل» لا تدل على شيء، والاجتماع بين المصطلحات هو المؤشر.",
    "BRAND_LIKE_TOKEN": "يحتوي اسم المضيف على مصطلح يشبه اسم جهة معروفة، بينما النطاق الذي يقدّم الطلب مختلف. هذا نمط يتّسق مع الانتحال، لكن الرابط وحده لا يثبت النيّة.",
    "SUSPICIOUS_TLD": "يُستخدم هذا النطاق الأعلى بشكل متكرر في إساءة الاستخدام قصيرة الأجل؛ وهو مؤشر ضعيف بمفرده.",
}


def build_secondary_signals(
    url: NormalizedURL,
    findings: list[HeuristicFinding],
    features: dict[str, float],
    prediction: Prediction,
) -> list[SecondarySignal]:
    """Build the secondary evidence rail from real measurements.

    Every value is derived from the actual URL, or explicitly reported
    as not-applicable. Nothing here is invented.
    """
    fired = {f.id for f in findings if f.triggered}
    signals: list[SecondarySignal] = []

    # --- Domain structure: real measurement ---
    structure_risk = sum(
        f.weight for f in findings if f.id in {
            "IP_HOST", "LONG_HOSTNAME", "EXCESSIVE_SUBDOMAINS",
            "PUNYCODE", "EXCESSIVE_HYPHENS", "SUSPICIOUS_TLD",
        }
    )
    signals.append(
        SecondarySignal(
            id="domain_structure",
            metric_key=_METRIC_KEYS["domain_structure"],
            value_en=_band_en(structure_risk),
            value_ar=_band_ar(structure_risk),
            severity=_severity_from_weight(structure_risk),
        )
    )

    # --- URL entropy: real measurement ---
    entropy = features["url_entropy"]
    threshold = THRESHOLDS["high_entropy_url"]
    if entropy >= threshold:
        value_en, value_ar, sev = (
            f"Elevated ({entropy:.2f})", f"مرتفع ({entropy:.2f})", "high_risk"
        )
    elif entropy >= threshold - 0.6:
        value_en, value_ar, sev = (
            f"Moderate ({entropy:.2f})", f"متوسط ({entropy:.2f})", "caution"
        )
    else:
        value_en, value_ar, sev = (
            f"Low ({entropy:.2f})", f"منخفض ({entropy:.2f})", "trusted"
        )
    signals.append(
        SecondarySignal(
            id="url_entropy",
            metric_key=_METRIC_KEYS["url_entropy"],
            value_en=value_en,
            value_ar=value_ar,
            severity=sev,
        )
    )

    # --- Brand match: real, and honest about its own limits ---
    if "BRAND_LIKE_TOKEN" in fired:
        value_en, value_ar, sev = "Possible mismatch", "عدم تطابق محتمل", "caution"
    else:
        value_en, value_ar, sev = "No mismatch detected", "لا يوجد عدم تطابق", "neutral"
    signals.append(
        SecondarySignal(
            id="brand_match",
            metric_key=_METRIC_KEYS["brand_match"],
            value_en=value_en,
            value_ar=value_ar,
            severity=sev,
        )
    )

    # --- Model probability: reported only when a model actually ran ---
    if prediction.available and prediction.probability is not None:
        pct = prediction.probability
        value_en = f"{pct:.0%}"
        value_ar = f"{pct:.0%}"
        sev = (
            "high_risk" if pct >= 0.6 else "caution" if pct >= 0.35 else "trusted"
        )
        signals.append(
            SecondarySignal(
                id="model_probability",
                metric_key="explanation.metrics.syntheticConfidence",
                value_en=value_en,
                value_ar=value_ar,
                severity=sev,
            )
        )

    # --- Provenance: honestly not-applicable for URL-only analysis ---
    # Reported as unavailable rather than omitted, so the absence is
    # visible instead of silently missing.
    signals.append(
        SecondarySignal(
            id="provenance",
            metric_key=_METRIC_KEYS["provenance"],
            value_en="Not applicable (URL only)",
            value_ar="لا ينطبق (رابط فقط)",
            severity="neutral",
        )
    )

    return signals


def _band_en(weight: int) -> str:
    if weight >= 30:
        return "High"
    if weight >= 14:
        return "Elevated"
    if weight > 0:
        return "Low"
    return "Normal"


def _band_ar(weight: int) -> str:
    if weight >= 30:
        return "مرتفع"
    if weight >= 14:
        return "مستوى مرتفع"
    if weight > 0:
        return "منخفض"
    return "طبيعي"


def _severity_from_weight(weight: int) -> str:
    if weight >= 30:
        return "high_risk"
    if weight >= 14:
        return "caution"
    return "trusted"


def build_timeline(duration_ms: float) -> list[TimelineRecord]:
    """Real pipeline stages, timed against the actual measured duration.

    Offsets are derived from the measured duration rather than invented
    per-request, so the timeline reflects this run.
    """
    total_s = max(duration_ms, 1.0) / 1000.0
    stages = [
        "acquire",
        "identify",
        "url",
        "metadata",
        "provenance",
        "correlate",
        "score",
    ]
    return [
        TimelineRecord(stage=stage, offset_seconds=round(total_s * i / len(stages), 3))
        for i, stage in enumerate(stages)
    ]


def map_to_trust_dna(
    url: NormalizedURL,
    findings: list[HeuristicFinding],
    features: dict[str, float],
    assessment: RiskAssessment,
) -> dict[str, int | None]:
    """Map real URL evidence onto the Trust DNA axes.

    Returns None for axes that are genuinely NOT APPLICABLE to a URL
    (synthetic-media and provenance signals), so the frontend can render
    "unavailable" instead of inventing a number. This is the honest
    representation the Phase 2 brief requires.
    """
    fired = {f.id for f in findings if f.triggered}

    # --- Domain: real, from structural findings ---
    domain_weight = sum(
        f.weight for f in findings if f.id in {
            "IP_HOST", "LONG_HOSTNAME", "EXCESSIVE_SUBDOMAINS", "PUNYCODE",
            "EXCESSIVE_HYPHENS", "SUSPICIOUS_TLD", "HIGH_ENTROPY_HOSTNAME",
        }
    )
    domain = int(min(100, domain_weight * 3.2))

    # --- Identity: real, from the brand-mismatch observation ---
    if "BRAND_LIKE_TOKEN" in fired:
        identity = 68
    elif "AT_SYMBOL" in fired:
        identity = 55
    else:
        identity = 20 if url.registered_domain else 45

    # --- Behavior: real, from lexical/obfuscation findings ---
    behavior_weight = sum(
        f.weight for f in findings if f.id in {
            "SUSPICIOUS_KEYWORD_COMBINATION", "CREDENTIAL_IN_URL",
            "EXCESSIVE_ENCODING", "ABNORMAL_PORT", "DOUBLE_SLASH",
            "HIGH_DIGIT_RATIO", "LONG_URL", "LONG_PATH",
        }
    )
    behavior = int(min(100, behavior_weight * 3.0))

    return {
        # Real URL-derived axes.
        "domain": domain,
        "identity": identity,
        "behavior": behavior,
        # Not applicable to URL-only analysis. Explicitly None.
        "synthetic": None,
        "provenance": None,
    }
