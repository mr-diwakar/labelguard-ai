import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text } from 'react-native';

import { colors, radii, shadows, spacing, typography } from '../theme';

interface QuickActionCardProps {
  label: string;
  icon: keyof typeof Ionicons.glyphMap;
  onPress: () => void;
}

export function QuickActionCard({ label, icon, onPress }: QuickActionCardProps) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      onPress={onPress}
      style={({ pressed }) => [styles.card, pressed && styles.pressed]}
    >
      <Ionicons name={icon} size={22} color={colors.primary} />
      <Text style={styles.label} numberOfLines={2}>
        {label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    minHeight: 92,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.sm,
    backgroundColor: colors.surface,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.border,
    ...shadows.card,
  },
  pressed: {
    backgroundColor: colors.surfaceMuted,
  },
  label: {
    ...typography.caption,
    color: colors.textPrimary,
    textAlign: 'center',
  },
});
