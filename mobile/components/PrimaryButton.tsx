import { Ionicons } from '@expo/vector-icons';
import { useRef } from 'react';
import { Animated, Pressable, StyleProp, StyleSheet, Text, ViewStyle } from 'react-native';

import { colors, radii, spacing, touchTarget, typography } from '../theme';

type ButtonVariant = 'primary' | 'light' | 'outline';

interface PrimaryButtonProps {
  label: string;
  onPress?: () => void;
  variant?: ButtonVariant;
  icon?: keyof typeof Ionicons.glyphMap;
  disabled?: boolean;
  fullWidth?: boolean;
  style?: StyleProp<ViewStyle>;
}

export function PrimaryButton({
  label,
  onPress,
  variant = 'primary',
  icon,
  disabled = false,
  fullWidth = false,
  style,
}: PrimaryButtonProps) {
  const scale = useRef(new Animated.Value(1)).current;

  const animateTo = (value: number) => {
    Animated.spring(scale, { toValue: value, useNativeDriver: true, speed: 40, bounciness: 0 }).start();
  };

  const contentColor = variant === 'primary' ? colors.textInverse : colors.primary;

  return (
    <Animated.View style={[{ transform: [{ scale }] }, fullWidth && styles.fullWidth, style]}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={label}
        accessibilityState={{ disabled }}
        disabled={disabled}
        onPress={onPress}
        onPressIn={() => animateTo(0.97)}
        onPressOut={() => animateTo(1)}
        style={[styles.base, styles[variant], disabled && styles.disabled]}
      >
        {icon && <Ionicons name={icon} size={18} color={disabled ? colors.textMuted : contentColor} />}
        <Text style={[styles.label, { color: disabled ? colors.textMuted : contentColor }]}>{label}</Text>
      </Pressable>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  base: {
    minHeight: touchTarget,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.md,
    borderRadius: radii.md,
    borderWidth: 1,
  },
  primary: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  light: {
    backgroundColor: colors.surface,
    borderColor: colors.surface,
  },
  outline: {
    backgroundColor: 'transparent',
    borderColor: colors.primaryBorder,
  },
  disabled: {
    backgroundColor: colors.surfaceMuted,
    borderColor: colors.border,
  },
  fullWidth: {
    alignSelf: 'stretch',
  },
  label: {
    ...typography.cardTitle,
  },
});
