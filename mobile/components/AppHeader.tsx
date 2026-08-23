import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radii, spacing, touchTarget, typography } from '../theme';

interface AppHeaderProps {
  title: string;
  subtitle?: string;
  /** Small line above the title, used for the Home greeting. */
  greeting?: string;
  showBrandMark?: boolean;
  onBackPress?: () => void;
  backLabel?: string;
  actionIcon?: keyof typeof Ionicons.glyphMap;
  actionLabel?: string;
  onActionPress?: () => void;
}

export function AppHeader({
  title,
  subtitle,
  greeting,
  showBrandMark = false,
  onBackPress,
  backLabel,
  actionIcon,
  actionLabel,
  onActionPress,
}: AppHeaderProps) {
  return (
    <View style={styles.container}>
      {onBackPress && (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={backLabel ?? 'Back'}
          onPress={onBackPress}
          hitSlop={8}
          style={({ pressed }) => [styles.iconButton, pressed && styles.iconButtonPressed]}
        >
          <Ionicons name="arrow-back" size={20} color={colors.primary} />
        </Pressable>
      )}

      <View style={styles.titleGroup}>
        {showBrandMark && (
          <View style={styles.brandMark}>
            <Ionicons name="shield-checkmark" size={22} color={colors.textInverse} />
          </View>
        )}
        <View style={styles.titleTexts}>
          {greeting && <Text style={styles.greeting}>{greeting}</Text>}
          <Text style={styles.title} numberOfLines={1}>
            {title}
          </Text>
          {subtitle && <Text style={styles.subtitle}>{subtitle}</Text>}
        </View>
      </View>

      {actionIcon && (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={actionLabel ?? 'Settings'}
          onPress={onActionPress}
          hitSlop={8}
          style={({ pressed }) => [styles.iconButton, pressed && styles.iconButtonPressed]}
        >
          <Ionicons name={actionIcon} size={20} color={colors.primary} />
        </Pressable>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.md,
    paddingBottom: spacing.lg,
  },
  titleGroup: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  brandMark: {
    width: 42,
    height: 42,
    borderRadius: radii.md,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  titleTexts: {
    flex: 1,
  },
  greeting: {
    ...typography.greeting,
    color: colors.textMuted,
    marginBottom: 2,
  },
  title: {
    ...typography.screenTitle,
    color: colors.textPrimary,
  },
  subtitle: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 2,
  },
  iconButton: {
    width: touchTarget,
    height: touchTarget,
    borderRadius: radii.md,
    backgroundColor: colors.primarySoft,
    borderWidth: 1,
    borderColor: colors.primaryBorder,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconButtonPressed: {
    backgroundColor: colors.primaryBorder,
  },
});
