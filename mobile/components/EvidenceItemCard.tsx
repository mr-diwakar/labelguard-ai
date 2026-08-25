import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { EVIDENCE_TYPE_PRESENTATION } from '../constants/verification';
import { colors, radii, shadows, spacing, typography } from '../theme';
import { EvidenceItem } from '../types/inspection';
import { formatConfidence } from '../utils/formatConfidence';
import { formatRelativeDate } from '../utils/formatRelativeDate';

interface EvidenceItemCardProps {
  item: EvidenceItem;
  onPress?: () => void;
}

/** One evidence artefact in the list: icon, title, a short summary and meta. */
export function EvidenceItemCard({ item, onPress }: EvidenceItemCardProps) {
  const { t } = useTranslation();
  const presentation = EVIDENCE_TYPE_PRESENTATION[item.type];
  const title = item.title ?? t(item.titleKey ?? presentation.labelKey);

  const values: string[] = [];
  if (item.expectedValue) {
    values.push(`${t('evidence.expectedValue')} ${item.expectedValue}`);
  }
  if (item.observedValue) {
    values.push(`${t('evidence.observedValue')} ${item.observedValue}`);
  }

  const summary = item.note ?? (values.length > 0 ? values.join('  ·  ') : undefined);

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={title}
      onPress={onPress}
      style={({ pressed }) => [styles.card, pressed && styles.pressed]}
    >
      <View style={styles.iconWrap}>
        <Ionicons name={presentation.icon} size={20} color={colors.primary} />
      </View>

      <View style={styles.content}>
        <View style={styles.titleRow}>
          <Text style={styles.title} numberOfLines={1}>
            {title}
          </Text>
          {item.isPlaceholder && (
            <View style={styles.tag}>
              <Text style={styles.tagText}>{t('evidence.placeholderBadge')}</Text>
            </View>
          )}
        </View>

        {summary && (
          <Text style={styles.summary} numberOfLines={2}>
            {summary}
          </Text>
        )}

        <Text style={styles.meta}>
          {item.confidence !== undefined && `${t('evidence.confidence')} ${formatConfidence(item.confidence)} · `}
          {formatRelativeDate(item.capturedAt, t)}
        </Text>
      </View>

      <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    padding: spacing.lg,
    backgroundColor: colors.surface,
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.border,
    ...shadows.card,
  },
  pressed: {
    backgroundColor: colors.surfaceMuted,
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
  content: {
    flex: 1,
    gap: spacing.xs,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  title: {
    ...typography.cardTitle,
    color: colors.textPrimary,
    flexShrink: 1,
  },
  tag: {
    paddingHorizontal: spacing.xs,
    paddingVertical: 2,
    borderRadius: radii.sm,
    backgroundColor: colors.surfaceMuted,
    borderWidth: 1,
    borderColor: colors.border,
  },
  tagText: {
    ...typography.label,
    fontSize: 9,
    color: colors.textMuted,
  },
  summary: {
    ...typography.body,
    color: colors.textSecondary,
  },
  meta: {
    ...typography.caption,
    fontWeight: '400',
    color: colors.textMuted,
  },
});
