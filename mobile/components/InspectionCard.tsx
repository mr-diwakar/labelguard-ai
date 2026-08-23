import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { STATUS_PRESENTATION } from '../constants/compliance';
import { colors, radii, shadows, spacing, typography } from '../theme';
import { Inspection } from '../types/inspection';
import { formatRelativeDate } from '../utils/formatRelativeDate';
import { StatusBadge } from './StatusBadge';

interface InspectionCardProps {
  inspection: Inspection;
  onPress?: () => void;
}

export function InspectionCard({ inspection, onPress }: InspectionCardProps) {
  const { t } = useTranslation();
  const presentation = STATUS_PRESENTATION[inspection.assessment.status];
  const relativeDate = formatRelativeDate(inspection.inspectedAt, t);

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`${inspection.productName}, ${t(presentation.labelKey)}, ${relativeDate}`}
      onPress={onPress}
      style={({ pressed }) => [styles.card, pressed && styles.pressed]}
    >
      <View
        style={[
          styles.iconWrap,
          { backgroundColor: presentation.softBackground, borderColor: presentation.border },
        ]}
      >
        <Ionicons name={presentation.icon} size={20} color={presentation.tint} />
      </View>

      <View style={styles.content}>
        <Text style={styles.productName} numberOfLines={1}>
          {inspection.productName}
        </Text>
        <StatusBadge status={inspection.assessment.status} />
        <Text style={styles.meta}>
          {relativeDate}
          {inspection.category ? ` · ${inspection.category}` : ''}
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
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  content: {
    flex: 1,
    gap: spacing.xs,
  },
  productName: {
    ...typography.cardTitle,
    color: colors.textPrimary,
  },
  meta: {
    ...typography.caption,
    fontWeight: '400',
    color: colors.textMuted,
  },
});
