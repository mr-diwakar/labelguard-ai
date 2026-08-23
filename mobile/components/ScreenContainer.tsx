import { ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { colors, spacing } from '../theme';

interface ScreenContainerProps {
  children: ReactNode;
  /** Set to false when the screen renders its own scrolling list. */
  padded?: boolean;
}

export function ScreenContainer({ children, padded = true }: ScreenContainerProps) {
  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <View style={[styles.content, padded && styles.padded]}>{children}</View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    flex: 1,
  },
  padded: {
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.lg,
  },
});
