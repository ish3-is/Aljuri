import type { TranslationKey } from '../i18n/translations'

/* ============================================================
   INTELLIGENCE TICKER CONTENT

   THE CONTENT POLICY, which is stricter than it looks:

   Every line is educational and NON-NUMERICAL. There is no
   statistic, percentage, study figure, incident count, prevalence
   claim or threat-volume number anywhere in this file — not because
   it would be hard to find, but because none of them could be
   cited. A ticker is read in peripheral vision; an unsourced number
   there becomes an unsourced number everywhere. So each item is a
   BEHAVIOURAL INSTRUCTION or a DISTINCTION, both of which are true
   without any measurement behind them.

   Each item also carries a category tag, so the strip teaches the
   taxonomy of digital trust as well as the individual tips.

   The Arabic is a full translation, not a summary: a reader in
   Arabic gets the same instruction, at the same level of detail.
   ============================================================ */

export interface TickerItem {
  id: string
  categoryKey: TranslationKey
  textEn: string
  textAr: string
}

/**
 * Key order defines the order items appear, and the set must be
 * long enough that the duplicated track is wider than the viewport
 * at every breakpoint — otherwise the -50% loop point would come
 * back into view before the first item has scrolled off, and the
 * seam would be visible as a jump. Twelve items at ~380px each is
 * roughly 4500px of track, which covers a 1400px viewport twice
 * over with margin.
 */
export const tickerItems: TickerItem[] = [
  {
    id: 'hoverOverDomain',
    categoryKey: 'ticker.categories.phishing',
    textEn: 'Read the domain before the message. Urgency and authority are the two oldest lures in phishing.',
    textAr: 'اقرأ النطاق قبل الرسالة. الإلحاح والسلطة هما أقدم خدعتين في التصيّد.',
  },
  {
    id: 'qrUnknownDestination',
    categoryKey: 'ticker.categories.qrSafety',
    textEn: 'A QR code can hide its destination until it is scanned. Resolve where it leads before you follow it.',
    textAr: 'قد يُخفي رمز QR وجهته حتى يُمسح. تحقّق من الوجهة قبل اتباعه.',
  },
  {
    id: 'mismatchBrand',
    categoryKey: 'ticker.categories.digitalTrust',
    textEn: 'A familiar logo does not make a message genuine. Compare the sender address, not the branding.',
    textAr: 'الشعار المألوف لا يجعل الرسالة حقيقية. قارن عنوان المرسل لا العلامة.',
  },
  {
    id: 'tooMuchInformation',
    categoryKey: 'ticker.categories.socialEngineering',
    textEn: 'Requests for credentials, transfers or urgency are signals in themselves. Pause before responding.',
    textAr: 'طلبات البيانات أو التحويلات أو الاستعجال هي إشارات بذاتها. توقّف قبل الرد.',
  },
  {
    id: 'reverseImageSearch',
    categoryKey: 'ticker.categories.syntheticMedia',
    textEn: 'Look for physical inconsistency before trusting an image: text on signs, reflections, and the edges of hands.',
    textAr: 'ابحث عن عدم اتساق مادي قبل الوثوق بصورة: النصوص على اللافتات والانعكاسات وحدود الأيدي.',
  },
  {
    id: 'metadataRemains',
    categoryKey: 'ticker.categories.syntheticMedia',
    textEn: 'Editing a file often leaves metadata behind. Its presence is a clue, and its absence is not a clean bill of health.',
    textAr: 'غالباً ما يترك التعديل بيانات وصفية. وجودها دليل، وغيابها ليس شهادة بخلوّ الملف.',
  },
  {
    id: 'shortenerHidesTarget',
    categoryKey: 'ticker.categories.phishing',
    textEn: 'A shortened link conceals its final destination. Expand it before you decide whether to open it.',
    textAr: 'الرابط المختصر يخفي وجهته النهائية. وسّعه قبل أن تقرر فتحه.',
  },
  {
    id: 'credentialsNeverRequested',
    categoryKey: 'ticker.categories.socialEngineering',
    textEn: 'No legitimate organisation asks for your password by message. That request is the attack.',
    textAr: 'لا تطلب أي جهة شرعية كلمة مرورك عبر رسالة. هذا الطلب هو الهجوم.',
  },
  {
    id: 'provenanceNotDecoration',
    categoryKey: 'ticker.categories.digitalTrust',
    textEn: 'Content credentials describe how a file was produced. They are evidence of process, not proof of truth.',
    textAr: 'بيانات الاعتماد تصف كيفية إنتاج الملف. هي دليل على العملية لا إثبات على الصحة.',
  },
  {
    id: 'encodedContentExists',
    categoryKey: 'ticker.categories.digitalTrust',
    textEn: 'Content can be concealed inside a file rather than displayed by it. A clean preview is not the whole file.',
    textAr: 'يمكن إخفاء المحتوى داخل الملف بدل عرضه. المعاينة النظيفة ليست الملف بأكمله.',
  },
  {
    id: 'manipulatedContext',
    categoryKey: 'ticker.categories.syntheticMedia',
    textEn: 'An unaltered image placed in a false context is still misleading. Check where it appeared, not only how it looks.',
    textAr: 'صورة غير معدّلة في سياق كاذب تظل مضلّلة. تحقّق من مكان ظهورها لا من شكلها فقط.',
  },
  {
    id: 'verifyOutOfBand',
    categoryKey: 'ticker.categories.phishing',
    textEn: 'If a request matters, confirm it through a channel you already trust — not the one the message supplied.',
    textAr: 'إذا كان الطلب مهماً، أكّده عبر قناة تثق بها مسبقاً — لا القناة التي أرسلتها الرسالة.',
  },
]