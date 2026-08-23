import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text } from 'react-native';

import { colors, radii, spacing, typography } from '../theme';

interface IntelligenceTileProps {
  label: string;
  icon: keyof typeof Ionicons.glyphMap;
  onPress: () => void;
}

/**
 * Deliberately quieter than the compliance cards: secondary product insights.
 */
export function IntelligenceTile({ label, icon, onPress }: IntelligenceTileProps) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      onPress={onPress}
      style={({ pressed }) => [styles.tile, pressed && styles.pressed]}
    >
      <Ionicons name={icon} size={18} color={colors.textSecondary} />
      <Text style={styles.label} numberOfLines={2}>
        {label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  tile: {
    flex: 1,
    minHeight: 76,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.sm,
    backgroundColor: colors.surfaceMuted,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  pressed: {
    backgroundColor: colors.divider,
  },
  label: {
    ...typography.caption,
    fontWeight: '500',
    color: colors.textSecondary,
    textAlign: 'center',
  },
});
