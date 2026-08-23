import { StyleSheet, Text, View } from 'react-native';

import { colors, radii, spacing, typography } from '../theme';
import { AnimatedCounter } from './AnimatedCounter';

interface StatCardProps {
  value: number;
  label: string;
  /** Accent used for the value and the top rule; defaults to the primary navy. */
  tint?: string;
  animate?: boolean;
}

export function StatCard({ value, label, tint = colors.primary, animate = true }: StatCardProps) {
  return (
    <View style={styles.card} accessibilityLabel={`${value} ${label}`}>
      <View style={[styles.rule, { backgroundColor: tint }]} />
      {animate ? (
        <AnimatedCounter value={value} style={[styles.value, { color: tint }]} />
      ) : (
        <Text style={[styles.value, { color: tint }]}>{value}</Text>
      )}
      <Text style={styles.label} numberOfLines={2}>
        {label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    minWidth: 68,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.sm,
    backgroundColor: colors.surface,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'flex-start',
  },
  rule: {
    width: 20,
    height: 3,
    borderRadius: radii.pill,
    marginBottom: spacing.sm,
  },
  value: {
    ...typography.stat,
  },
  label: {
    ...typography.caption,
    fontWeight: '400',
    color: colors.textSecondary,
    marginTop: 2,
  },
});
