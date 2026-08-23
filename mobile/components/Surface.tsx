import { ReactNode } from 'react';
import { StyleProp, StyleSheet, View, ViewStyle } from 'react-native';

import { colors, radii, shadows, spacing } from '../theme';

interface SurfaceProps {
  children: ReactNode;
  style?: StyleProp<ViewStyle>;
  padded?: boolean;
}

/**
 * Shared white card shell so every card in the app has the same
 * border, radius and elevation.
 */
export function Surface({ children, style, padded = true }: SurfaceProps) {
  return <View style={[styles.surface, padded && styles.padded, style]}>{children}</View>;
}

const styles = StyleSheet.create({
  surface: {
    backgroundColor: colors.surface,
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.border,
    ...shadows.card,
  },
  padded: {
    padding: spacing.lg,
  },
});
