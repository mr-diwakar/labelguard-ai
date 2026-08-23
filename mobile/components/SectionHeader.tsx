import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, spacing, typography } from '../theme';

interface SectionHeaderProps {
  title: string;
  description?: string;
  actionLabel?: string;
  onActionPress?: () => void;
}

export function SectionHeader({ title, description, actionLabel, onActionPress }: SectionHeaderProps) {
  return (
    <View style={styles.container}>
      <View style={styles.texts}>
        <Text style={styles.title}>{title}</Text>
        {description && <Text style={styles.description}>{description}</Text>}
      </View>

      {actionLabel && (
        <Pressable accessibilityRole="button" onPress={onActionPress} hitSlop={8}>
          <Text style={styles.action}>{actionLabel}</Text>
        </Pressable>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: spacing.md,
    marginBottom: spacing.md,
  },
  texts: {
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
  action: {
    ...typography.caption,
    color: colors.primaryMuted,
    paddingTop: 2,
  },
});
