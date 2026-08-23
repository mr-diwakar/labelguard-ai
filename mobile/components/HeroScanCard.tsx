import { Ionicons } from '@expo/vector-icons';
import { useEffect, useRef } from 'react';
import { Animated, Easing, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { colors, motion, radii, shadows, spacing, typography } from '../theme';
import { PrimaryButton } from './PrimaryButton';

interface HeroScanCardProps {
  onScanPress: () => void;
}

/**
 * Dominant call to action on the Home screen. A slow halo behind the scan icon
 * signals "ready to scan" without animating the whole card.
 */
export function HeroScanCard({ onScanPress }: HeroScanCardProps) {
  const { t } = useTranslation();
  const breathe = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(breathe, {
          toValue: 1,
          duration: motion.breathe,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.timing(breathe, {
          toValue: 0,
          duration: motion.breathe,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
      ]),
    );

    loop.start();

    return () => loop.stop();
  }, [breathe]);

  const haloScale = breathe.interpolate({ inputRange: [0, 1], outputRange: [1, 1.18] });
  const haloOpacity = breathe.interpolate({ inputRange: [0, 1], outputRange: [0.35, 0] });

  return (
    <View style={styles.card}>
      <View style={styles.topRow}>
        <View style={styles.iconArea}>
          <Animated.View
            pointerEvents="none"
            style={[styles.halo, { opacity: haloOpacity, transform: [{ scale: haloScale }] }]}
          />
          <View style={styles.iconWrap}>
            <Ionicons name="scan" size={30} color={colors.textInverse} />
          </View>
        </View>

        <View style={styles.tag}>
          <Text style={styles.tagText}>{t('common.aiAssisted')}</Text>
        </View>
      </View>

      <Text style={styles.title}>{t('home.scanTitle')}</Text>
      <Text style={styles.description}>{t('home.scanDescription')}</Text>

      <PrimaryButton
        label={t('home.scanCta')}
        variant="light"
        icon="camera-outline"
        onPress={onScanPress}
        fullWidth
        style={styles.button}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.primary,
    borderRadius: radii.xl,
    padding: spacing.xl,
    ...shadows.raised,
  },
  topRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: spacing.lg,
  },
  iconArea: {
    width: 56,
    height: 56,
    alignItems: 'center',
    justifyContent: 'center',
  },
  halo: {
    position: 'absolute',
    width: 56,
    height: 56,
    borderRadius: radii.lg,
    backgroundColor: colors.textInverse,
  },
  iconWrap: {
    width: 56,
    height: 56,
    borderRadius: radii.lg,
    backgroundColor: colors.primaryMuted,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tag: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 5,
    borderRadius: radii.sm,
    borderWidth: 1,
    borderColor: colors.primaryMuted,
  },
  tagText: {
    ...typography.label,
    color: colors.textInverseMuted,
  },
  title: {
    ...typography.heroTitle,
    color: colors.textInverse,
  },
  description: {
    ...typography.body,
    color: colors.textInverseMuted,
    marginTop: spacing.sm,
  },
  button: {
    marginTop: spacing.xl,
  },
});
