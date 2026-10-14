import { motion } from 'motion/react'
import { useI18n } from '../../i18n/useI18n'
import type { TranslationKey } from '../../i18n/translations'
import type { ImageMetadataDetail } from '../../types/analysis'

/* ============================================================
   IMAGE METADATA PANEL

   A flat evidence table of what the file itself declares.

   Two deliberate constraints:

   · GPS IS A BOOLEAN. Whether location data is present is relevant to
     the assessment; WHERE the photo was taken is not BASIRAH's to
     surface, and the payload never carries coordinates anyway. The row
     says "Present" or "Not present" and nothing else.

   · ABSENT FIELDS ARE NOT INVENTED. A camera model that was not
     recorded renders as N/A, in the same muted mono treatment every
     other unmeasured value uses across the product. Substituting a
     blank string or a dash would make "we did not read this" look
     like "this was empty".
   ============================================================ */

interface ImageMetadataPanelProps {
  metadata: ImageMetadataDetail
  /** Object URL of the submitted file, when one survived the upload. */
  previewUrl?: string
}

interface Row {
  key: string
  labelKey: TranslationKey
  /** null renders as N/A. Never coerced to a placeholder value. */
  value: string | null
  /** Latin-script values stay LTR even inside an Arabic layout. */
  latin?: boolean
}

export function ImageMetadataPanel({
  metadata,
  previewUrl,
}: ImageMetadataPanelProps) {
  const { t, language } = useI18n()
  const isArabic = language === 'ar'

  const present = t('image.metadata.present')
  const absent = t('image.metadata.absent')
  const notAvailable = t('explanation.values.unavailable')

  const rows: Row[] = [
    { key: 'format', labelKey: 'image.metadata.format', value: metadata.format, latin: true },
    {
      key: 'dimensions',
      labelKey: 'image.metadata.dimensions',
      value: `${metadata.width} × ${metadata.height}`,
      latin: true,
    },
    { key: 'colour', labelKey: 'image.metadata.colourMode', value: metadata.colorMode, latin: true },
    {
      key: 'exif',
      labelKey: 'image.metadata.exif',
      value: metadata.exifPresent ? present : absent,
    },
    {
      key: 'camera',
      labelKey: 'image.metadata.camera',
      // Make and model are joined only when both exist; a lone model
      // string is shown on its own rather than padded with a null.
      value:
        metadata.cameraMake && metadata.cameraModel
          ? `${metadata.cameraMake} ${metadata.cameraModel}`
          : (metadata.cameraModel ?? metadata.cameraMake),
      latin: true,
    },
    { key: 'software', labelKey: 'image.metadata.software', value: metadata.software, latin: true },
    { key: 'created', labelKey: 'image.metadata.created', value: metadata.createdAt, latin: true },
    {
      key: 'orientation',
      labelKey: 'image.metadata.orientation',
      // 1 is the EXIF "normal" case and carries no information a reader
      // acts on; anything higher is the meaningful deviation.
      value: metadata.orientation === null ? null : String(metadata.orientation),
      latin: true,
    },
    {
      // Boolean only. No coordinates are requested, stored or rendered.
      key: 'gps',
      labelKey: 'image.metadata.gps',
      value: metadata.gpsPresent ? present : absent,
    },
  ]

  return (
    <div className="grid gap-6 sm:grid-cols-[180px_1fr] sm:gap-7">
      {/* ---------------- Preview ---------------- */}
      <div className="shrink-0">
        <div className="overflow-hidden rounded-md border border-line bg-surface-inset">
          {previewUrl ? (
            <img
              src={previewUrl}
              alt={t('image.metadata.previewAlt')}
              className="block aspect-square w-full object-cover"
              loading="lazy"
            />
          ) : (
            <div className="flex aspect-square w-full items-center justify-center p-4 text-center text-[0.7rem] text-text-dim">
              {t('image.metadata.noPreview')}
            </div>
          )}
        </div>
      </div>

      {/* ---------------- Field table ---------------- */}
      <div className="min-w-0">
        <dl className="divide-y divide-line/50">
          {rows.map((row, index) => (
            <motion.div
              key={row.key}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                delay: 0.1 + index * 0.035,
                duration: 0.3,
                ease: [0.16, 1, 0.3, 1],
              }}
              className="flex items-baseline justify-between gap-4 py-2.5"
            >
              <dt className="text-[0.78rem] text-text-dim">{t(row.labelKey)}</dt>
              <dd
                className={
                  row.value === null
                    ? 'font-mono text-[0.68rem] tracking-wider text-text-dim'
                    : row.latin
                      ? 'ltr-embed truncate text-[0.78rem] text-text-muted'
                      : 'text-[0.78rem] text-text-muted'
                }
              >
                {row.value === null ? notAvailable : row.value}
              </dd>
            </motion.div>
          ))}
        </dl>

        {/* The backend's own reading of the EXIF evidence, verbatim. */}
        <p className="mt-4 border-t border-line/50 pt-3.5 text-[0.78rem] leading-relaxed text-text-dim">
          {isArabic ? metadata.interpretationAr : metadata.interpretationEn}
        </p>
      </div>
    </div>
  )
}