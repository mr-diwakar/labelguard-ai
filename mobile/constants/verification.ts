import { Ionicons } from '@expo/vector-icons';
import { ComponentProps } from 'react';

import { colors } from '../theme';
import { EvidenceType, VerificationMethod, VerificationOutcome } from '../types/inspection';

type IoniconName = ComponentProps<typeof Ionicons>['name'];

export interface VerificationPresentation {
  /** Translation key for the uppercase chip wording. */
  badgeKey: string;
  /** Translation key for the sentence-case label. */
  labelKey: string;
  /** Translation key for the advisory helper line. */
  helperKey: string;
  /** Text glyph so status never depends on colour alone. */
  glyph: string;
  icon: IoniconName;
  tint: string;
  softBackground: string;
  border: string;
}

/**
 * Presentation for label-to-product verification outcomes.
 *
 * Kept separate from STATUS_PRESENTATION (legal compliance) on purpose: the two
 * result vocabularies must never be conflated (PROJECT_CONTEXT §7–8). The
 * consumer-facing wording is advisory ("potential mismatch"), never "fraud".
 */
export const VERIFICATION_PRESENTATION: Record<VerificationOutcome, VerificationPresentation> = {
  MATCH: {
    badgeKey: 'verification.matchBadge',
    labelKey: 'verification.matchLabel',
    helperKey: 'verification.matchHelper',
    glyph: '✓',
    icon: 'checkmark-circle',
    tint: colors.success,
    softBackground: colors.successSoft,
    border: colors.successBorder,
  },
  POTENTIAL_MISMATCH: {
    badgeKey: 'verification.mismatchBadge',
    labelKey: 'verification.mismatchLabel',
    helperKey: 'verification.mismatchHelper',
    glyph: '⚠',
    icon: 'alert-circle',
    tint: colors.warning,
    softBackground: colors.warningSoft,
    border: colors.warningBorder,
  },
  MANUAL_REVIEW: {
    badgeKey: 'verification.reviewBadge',
    labelKey: 'verification.reviewLabel',
    helperKey: 'verification.reviewHelper',
    glyph: '?',
    icon: 'search-circle',
    tint: colors.info,
    softBackground: colors.infoSoft,
    border: colors.infoBorder,
  },
  COULD_NOT_VERIFY: {
    badgeKey: 'verification.couldNotBadge',
    labelKey: 'verification.couldNotLabel',
    helperKey: 'verification.couldNotHelper',
    glyph: '?',
    icon: 'help-circle',
    tint: colors.textMuted,
    softBackground: colors.surfaceMuted,
    border: colors.border,
  },
  NOT_APPLICABLE: {
    badgeKey: 'verification.notApplicableBadge',
    labelKey: 'verification.notApplicableLabel',
    helperKey: 'verification.notApplicableHelper',
    glyph: '–',
    icon: 'remove-circle',
    tint: colors.textMuted,
    softBackground: colors.surfaceMuted,
    border: colors.border,
  },
};

export interface EvidenceTypePresentation {
  labelKey: string;
  icon: IoniconName;
}

/** Icon + label per evidence artefact type, used by the evidence list. */
export const EVIDENCE_TYPE_PRESENTATION: Record<EvidenceType, EvidenceTypePresentation> = {
  PRODUCT_IMAGE: { labelKey: 'evidence.typeProductImage', icon: 'cube-outline' },
  LABEL_IMAGE: { labelKey: 'evidence.typeLabelImage', icon: 'pricetag-outline' },
  HIGHLIGHTED_REGION: { labelKey: 'evidence.typeHighlighted', icon: 'scan-outline' },
  MEASUREMENT: { labelKey: 'evidence.typeMeasurement', icon: 'speedometer-outline' },
  NOTE: { labelKey: 'evidence.typeNote', icon: 'create-outline' },
};

/**
 * How an observed value was obtained, in plain language. Making the method
 * explicit keeps the app honest: a phone camera cannot weigh a product, so a
 * quantity check always reads as a manual measurement rather than a "scan".
 */
export const VERIFICATION_METHOD_LABEL_KEYS: Record<VerificationMethod, string> = {
  OCR: 'verification.methodOcr',
  USER_MEASUREMENT: 'verification.methodMeasurement',
  COMPUTER_VISION: 'verification.methodCv',
  MANUAL: 'verification.methodManual',
};
