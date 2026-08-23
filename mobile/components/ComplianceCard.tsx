import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { colors, radii, spacing, typography } from '../theme';
import { Surface } from './Surface';

interface ComplianceCardProps {
  /** Translation keys for the mandatory declarations that are inspected. */
  declarationKeys: string[];
}

/**
 * Presents Legal Metrology as the primary capability of the app. The checklist
 * describes what is inspected, not the outcome of any inspection.
 */
export function ComplianceCard({ declarationKeys }: ComplianceCardProps) {
  const { t } = useTranslation();

  return (
    <Surface>
      <View style={styles.header}>
        <View style={styles.iconWrap}>
          <Ionicons name="document-text-outline" size={20} color={colors.primary} />
        </View>
        <View style={styles.headerTexts}>
          <Text style={styles.title}>{t('compliance.title')}</Text>
          <Text style={styles.description}>{t('compliance.description')}</Text>
        </View>
      </View>

      <View style={styles.chipRow}>
        {declarationKeys.map((key) => (
          <View key={key} style={[styles.chip, styles.chipChecked]}>
            <Text style={[styles.chipGlyph, styles.chipCheckedText]}>✓</Text>
            <Text style={[styles.chipLabel, styles.chipCheckedText]}>{t(key)}</Text>
          </View>
        ))}

        <View style={[styles.chip, styles.chipReview]}>
          <Text style={[styles.chipGlyph, styles.chipReviewText]}>?</Text>
          <Text style={[styles.chipLabel, styles.chipReviewText]}>
            {t('declaration.manualReview')}
          </Text>
        </View>
      </View>

      <Text style={styles.footnote}>{t('compliance.footnote')}</Text>
    </Surface>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    gap: spacing.md,
  },
  iconWrap: {
    width: 40,
    height: 40,
    borderRadius: radii.md,
    backgroundColor: colors.primarySoft,
    borderWidth: 1,
    borderColor: colors.primaryBorder,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTexts: {
    flex: 1,
  },
  title: {
    ...typography.sectionTitle,
    color: colors.textPrimary,
  },
  description: {
    ...typography.body,
    color: colors.textSecondary,
    marginTop: spacing.xs,
  },
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    marginTop: spacing.lg,
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    paddingHorizontal: spacing.sm,
    paddingVertical: 6,
    borderRadius: radii.sm,
    borderWidth: 1,
  },
  chipChecked: {
    backgroundColor: colors.successSoft,
    borderColor: colors.successBorder,
  },
  chipReview: {
    backgroundColor: colors.infoSoft,
    borderColor: colors.infoBorder,
  },
  chipGlyph: {
    fontSize: 12,
    lineHeight: 16,
    fontWeight: '700',
  },
  chipLabel: {
    ...typography.caption,
  },
  chipCheckedText: {
    color: colors.success,
  },
  chipReviewText: {
    color: colors.info,
  },
  footnote: {
    ...typography.caption,
    fontWeight: '400',
    color: colors.textMuted,
    marginTop: spacing.lg,
  },
});
