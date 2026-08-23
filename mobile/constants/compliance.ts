import { Ionicons } from '@expo/vector-icons';
import { ComponentProps } from 'react';

import { colors } from '../theme';
import { ComplianceStatus } from '../types/inspection';

type IoniconName = ComponentProps<typeof Ionicons>['name'];

export interface StatusPresentation {
  /** Translation key for chips. */
  badgeKey: string;
  /** Translation key for headings and list rows. */
  labelKey: string;
  /** Wording that keeps the assessment advisory rather than a legal verdict. */
  helperKey: string;
  /** Text glyph so status never depends on colour alone. */
  glyph: string;
  icon: IoniconName;
  tint: string;
  softBackground: string;
  border: string;
}

export const STATUS_PRESENTATION: Record<ComplianceStatus, StatusPresentation> = {
  COMPLIANT: {
    badgeKey: 'status.compliantBadge',
    labelKey: 'status.compliantLabel',
    helperKey: 'status.helperAutomated',
    glyph: '✓',
    icon: 'checkmark-circle',
    tint: colors.success,
    softBackground: colors.successSoft,
    border: colors.successBorder,
  },
  POTENTIAL_NON_COMPLIANCE: {
    badgeKey: 'status.potentialBadge',
    labelKey: 'status.potentialLabel',
    helperKey: 'status.helperManual',
    glyph: '⚠',
    icon: 'alert-circle',
    tint: colors.warning,
    softBackground: colors.warningSoft,
    border: colors.warningBorder,
  },
  MANUAL_REVIEW: {
    badgeKey: 'status.reviewBadge',
    labelKey: 'status.reviewLabel',
    helperKey: 'status.helperManual',
    glyph: '?',
    icon: 'search-circle',
    tint: colors.info,
    softBackground: colors.infoSoft,
    border: colors.infoBorder,
  },
};

export type StatusFilterValue = ComplianceStatus | 'ALL';

export const STATUS_FILTERS: Array<{ labelKey: string; value: StatusFilterValue }> = [
  { labelKey: 'history.filterAll', value: 'ALL' },
  { labelKey: 'history.filterCompliant', value: 'COMPLIANT' },
  { labelKey: 'history.filterReview', value: 'MANUAL_REVIEW' },
  { labelKey: 'history.filterIssue', value: 'POTENTIAL_NON_COMPLIANCE' },
];
