import { StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { colors, spacing, typography } from '../theme';
import { InspectionAssessment } from '../types/inspection';

interface LegalCheckListProps {
  assessment: InspectionAssessment;
}

interface CheckRow {
  key: string;
  labelKey: string;
  glyph: string;
  tint: string;
  phraseKey: string;
}

/**
 * Consumer-friendly summary of the legal declaration checks. Deliberately
 * plain-language: "detected", "potential issue", "needs manual review" — never
 * "missing" or any wording that reads as a legal verdict.
 */
export function LegalCheckList({ assessment }: LegalCheckListProps) {
  const { t } = useTranslation();

  const rows: CheckRow[] = [
    ...assessment.passed.map((check, index) => ({
      key: `passed-${index}-${check.declarationKey}`,
      labelKey: check.declarationKey,
      glyph: '✓',
      tint: colors.success,
      phraseKey: 'result.declarationDetected',
    })),
    ...assessment.violations.map((check, index) => ({
      key: `violation-${index}-${check.declarationKey}`,
      labelKey: check.declarationKey,
      glyph: '⚠',
      tint: colors.warning,
      phraseKey: 'result.declarationIssue',
    })),
    ...assessment.manualReview.map((check, index) => ({
      key: `review-${index}-${check.declarationKey}`,
      labelKey: check.declarationKey,
      glyph: '?',
      tint: colors.info,
      phraseKey: 'result.declarationReview',
    })),
  ];

  return (
    <View style={styles.list}>
      {rows.map((row) => (
        <View key={row.key} style={styles.row}>
          <Text style={[styles.glyph, { color: row.tint }]}>{row.glyph}</Text>
          <Text style={styles.text}>{t(row.phraseKey, { label: t(row.labelKey) })}</Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  list: {
    gap: spacing.sm,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.sm,
  },
  glyph: {
    fontSize: 14,
    lineHeight: 20,
    fontWeight: '700',
  },
  text: {
    ...typography.body,
    color: colors.textPrimary,
    flex: 1,
  },
});
