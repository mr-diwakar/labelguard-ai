import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radii, shadows, spacing, typography } from '../theme';

interface NavRowProps {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  description?: string;
  onPress?: () => void;
  /** Small trailing chip, e.g. an item count or a "Soon" marker. */
  tag?: string;
}

/**
 * A tappable row that leads to another section. Used on the result screen to
 * link out to evidence, nutrition, ingredients and the planned sections.
 */
export function NavRow({ icon, label, description, onPress, tag }: NavRowProps) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      onPress={onPress}
      style={({ pressed }) => [styles.row, pressed && styles.pressed]}
    >
      <View style={styles.iconWrap}>
        <Ionicons name={icon} size={20} color={colors.primary} />
      </View>

      <View style={styles.content}>
        <Text style={styles.label} numberOfLines={1}>
          {label}
        </Text>
        {description && (
          <Text style={styles.description} numberOfLines={2}>
            {description}
          </Text>
        )}
      </View>

      {tag && (
        <View style={styles.tag}>
          <Text style={styles.tagText}>{tag}</Text>
        </View>
      )}

      <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
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
    gap: 2,
  },
  label: {
    ...typography.cardTitle,
    color: colors.textPrimary,
  },
  description: {
    ...typography.caption,
    fontWeight: '400',
    color: colors.textMuted,
  },
  tag: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 3,
    borderRadius: radii.pill,
    backgroundColor: colors.surfaceMuted,
    borderWidth: 1,
    borderColor: colors.border,
  },
  tagText: {
    ...typography.label,
    fontSize: 9,
    color: colors.textMuted,
  },
});
