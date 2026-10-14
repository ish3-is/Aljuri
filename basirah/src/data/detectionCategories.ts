/**
 * Detection category registry.
 *
 * The ordering encodes the product's actual priority: suspicious IMAGES
 * are listed first and marked as the primary modality, suspicious URLs
 * come fourth as the secondary one. Nothing here is aspirational — each
 * entry carries the state it is really in, and `planned` categories are
 * included deliberately so the roadmap is visible rather than implied.
 */

import type { TranslationKey } from '../i18n/translations'

export type ModuleState =
  | 'active'
  | 'researchGrade'
  | 'advisory'
  | 'planned'
  | 'comingSoon'
  | 'inDevelopment'
  | 'expanding'
  | 'capability'
  /**
   * PARTIAL support, stated as its own state.
   *
   * C2PA support can locate a manifest and attempt signature
   * validation, but it is not a full trust-list implementation.
   * "Active" would overstate it and "Planned" would understate it, so
   * it gets the word it actually deserves.
   */
  | 'limited'

export interface DetectionCategory {
  /** Stable id, also used as the translation key suffix. */
  id: string
  nameKey: TranslationKey
  bodyKey: TranslationKey
  state: ModuleState
  /** The primary modality is visually and structurally ranked first. */
  primary?: boolean
}

export const detectionCategories: DetectionCategory[] = [
  {
    id: 'images',
    nameKey: 'categories.images.name',
    bodyKey: 'categories.images.body',
    state: 'active',
    primary: true,
  },
  {
    id: 'files',
    nameKey: 'categories.files.name',
    bodyKey: 'categories.files.body',
    state: 'active',
  },
  {
    id: 'encoded',
    nameKey: 'categories.encoded.name',
    bodyKey: 'categories.encoded.body',
    state: 'active',
  },
  {
    id: 'urls',
    nameKey: 'categories.urls.name',
    bodyKey: 'categories.urls.body',
    state: 'advisory',
  },
  {
    id: 'ocr',
    nameKey: 'categories.ocr.name',
    bodyKey: 'categories.ocr.body',
    state: 'active',
  },
  {
    id: 'qr',
    nameKey: 'categories.qr.name',
    bodyKey: 'categories.qr.body',
    state: 'active',
  },
  {
    id: 'correlation',
    nameKey: 'categories.correlation.name',
    bodyKey: 'categories.correlation.body',
    state: 'expanding',
  },
  {
    id: 'c2pa',
    nameKey: 'categories.c2pa.name',
    bodyKey: 'categories.c2pa.body',
    state: 'limited',
  },
]