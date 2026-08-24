import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { VERIFICATION_METHOD_LABEL_KEYS, VERIFICATION_PRESENTATION } from '../constants/verification';
import { colors, radii, spacing, typography } from '../theme';
import { VerificationCheck } from '../types/inspection';
import { formatConfidence } from '../utils/formatConfidence';
import { Surface } from './Surface';
import { VerificationStatusBadge } from './VerificationStatusBadge';

interface DeclaredObservedRowProps {
  check: VerificationCheck;
  /** Shown as a "View evidence" affordance when supporting evidence exists. */
  onEvidencePress?: () => void;
}

/**
 * One label-to-product check, laid out as "declared → observed" so the
 * comparison reads at a glance. Missing observed values are stated plainly
 * ("could not be reliably verified") rather than shown as an error.
 */
export function DeclaredObservedRow({ check, onEvidencePress }: DeclaredObservedRowProps) {
  const { t } = useTranslation();
  const presentation = VERIFICATION_PRESENTATION[check.status];

  return (
    <Surface style={styles.card}>
      <View style={styles.header}>
        <Text style={styles.label}>{t(check.labelKey)}</Text>
        <VerificationStatusBadge status={check.status} />
      </View>

      <View style={styles.compareRow}>
        <View style={styles.compareCol}>
          <Text style={styles.compareLabel}>{t('verification.declared')}</Text>
          <Text style={styles.compareValue}>{check.declared ?? '—'}</Text>
        </View>
        <Ionicons name="arrow-forward" size={16} color={colors.textMuted} style={styles.arrow} />
        <View style={styles.compareCol}>
          <Text style={styles.compareLabel}>{t('verification.observed')}</Text>
          <Text
            style={[styles.compareValue, check.observed === undefined && styles.compareValueMuted]}
          >
            {check.observed ?? t('verification.couldNotVerifyValue')}
          </Text>
        </View>
      </View>

      {check.difference !== undefined && (
        <View
          style={[
            styles.differenceChip,
            { backgroundColor: presentation.softBackground, borderColor: presentation.border },
          ]}
        >
          <Text style={[styles.differenceText, { color: presentation.tint }]}>
            {t('verification.difference')}: {check.difference}
          </Text>
        </View>
      )}

      <View style={styles.metaRow}>
        {check.method && (
          <View style={styles.metaItem}>
            <Ionicons name="information-circle-outline" size={14} color={colors.textMuted} />
            <Text style={styles.metaText}>{t(VERIFICATION_METHOD_LABEL_KEYS[check.method])}</Text>
          </View>
        )}
        <View style={styles.metaItem}>
          <Ionicons name="stats-chart-outline" size={14} color={colors.textMuted} />
          <Text style={styles.metaText}>
            {t('evidence.confidence')}: {formatConfidence(check.confidence)}
          </Text>
        </View>
      </View>

      {onEvidencePress && (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={t('verification.viewEvidence')}
          onPress={onEvidencePress}
          style={({ pressed }) => [styles.evidenceLink, pressed && styles.evidenceLinkPressed]}
        >
          <Ionicons name="images-outline" size={16} color={colors.primary} />
          <Text style={styles.evidenceLinkText}>{t('verification.viewEvidence')}</Text>
        </Pressable>
      )}
    </Surface>
  );
}

const styles = StyleSheet.create({
  card: {
    gap: spacing.md,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.md,
  },
  label: {
    ...typography.cardTitle,
    color: colors.textPrimary,
    flex: 1,
  },
  compareRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  compareCol: {
    flex: 1,
    gap: 2,
  },
  arrow: {
    marginTop: spacing.md,
  },
  compareLabel: {
    ...typography.label,
    color: colors.textMuted,
  },
  compareValue: {
    ...typography.stat,
    fontSize: 18,
    lineHeight: 22,
    color: colors.textPrimary,
  },
  compareValueMuted: {
    ...typography.body,
    color: colors.textMuted,
  },
  differenceChip: {
    alignSelf: 'flex-start',
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
    borderRadius: radii.sm,
    borderWidth: 1,
  },
  differenceText: {
    ...typography.caption,
  },
  metaRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
  },
  metaItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
  },
  metaText: {
    ...typography.caption,
    fontWeight: '400',
    color: colors.textSecondary,
  },
  evidenceLink: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    alignSelf: 'flex-start',
  },
  evidenceLinkPressed: {
    opacity: 0.6,
  },
  evidenceLinkText: {
    ...typography.caption,
    color: colors.primary,
  },
});
