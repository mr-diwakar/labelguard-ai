import { Ionicons } from '@expo/vector-icons';
import { useEffect, useRef } from 'react';
import { Animated, Easing, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { colors, motion, radii, spacing, typography } from '../theme';

export type ProcessingStepState = 'pending' | 'active' | 'done';

interface ProcessingStepRowProps {
  label: string;
  state: ProcessingStepState;
}

const STATE_LABEL_KEYS: Record<ProcessingStepState, string> = {
  pending: 'processing.pending',
  active: 'processing.active',
  done: 'processing.done',
};

export function ProcessingStepRow({ label, state }: ProcessingStepRowProps) {
  const { t } = useTranslation();
  const progress = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (state !== 'active') {
      progress.setValue(state === 'done' ? 1 : 0);
      return;
    }

    const loop = Animated.loop(
      Animated.timing(progress, {
        toValue: 1,
        duration: 900,
        easing: Easing.inOut(Easing.ease),
        useNativeDriver: true,
      }),
    );

    progress.setValue(0);
    loop.start();

    return () => loop.stop();
  }, [progress, state]);

  const isDone = state === 'done';
  const isActive = state === 'active';
  const tint = isDone ? colors.success : isActive ? colors.primary : colors.textMuted;

  return (
    <View style={styles.row}>
      <View
        style={[
          styles.marker,
          isDone && styles.markerDone,
          isActive && styles.markerActive,
        ]}
      >
        {isDone ? (
          <Ionicons name="checkmark" size={14} color={colors.textInverse} />
        ) : (
          <Animated.View
            style={[
              styles.pulse,
              {
                backgroundColor: isActive ? colors.primary : colors.textMuted,
                opacity: isActive
                  ? progress.interpolate({ inputRange: [0, 0.5, 1], outputRange: [0.3, 1, 0.3] })
                  : 0.4,
              },
            ]}
          />
        )}
      </View>

      <Text style={[styles.label, (isDone || isActive) && styles.labelStrong]} numberOfLines={1}>
        {label}
      </Text>

      <Text style={[styles.state, { color: tint }]}>{t(STATE_LABEL_KEYS[state])}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    paddingVertical: spacing.md,
  },
  marker: {
    width: 26,
    height: 26,
    borderRadius: radii.pill,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceMuted,
    alignItems: 'center',
    justifyContent: 'center',
  },
  markerActive: {
    borderColor: colors.primaryBorder,
    backgroundColor: colors.primarySoft,
  },
  markerDone: {
    borderColor: colors.success,
    backgroundColor: colors.success,
  },
  pulse: {
    width: 10,
    height: 10,
    borderRadius: radii.pill,
  },
  label: {
    flex: 1,
    ...typography.body,
    color: colors.textMuted,
  },
  labelStrong: {
    color: colors.textPrimary,
    fontWeight: '600',
  },
  state: {
    ...typography.caption,
  },
});
