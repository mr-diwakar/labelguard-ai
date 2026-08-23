import { useEffect, useRef, useState } from 'react';
import { Animated, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { AppHeader } from '../components/AppHeader';
import { PrimaryButton } from '../components/PrimaryButton';
import { ProcessingStepRow, ProcessingStepState } from '../components/ProcessingStepRow';
import { ScreenContainer } from '../components/ScreenContainer';
import { Surface } from '../components/Surface';
import { ProcessingScreenProps } from '../navigation/types';
import { colors, motion, radii, spacing, typography } from '../theme';

const STEP_KEYS = [
  'processing.imageQuality',
  'processing.ocr',
  'processing.extraction',
  'processing.validation',
  'processing.evidence',
];

/** Mock timing only; the real durations will come from the scan API. */
const STEP_DURATION_MS = 900;

export function ProcessingScreen({ navigation, route }: ProcessingScreenProps) {
  const { t } = useTranslation();
  const { inspectionId } = route.params;
  const [completedSteps, setCompletedSteps] = useState(0);
  const barProgress = useRef(new Animated.Value(0)).current;

  const isComplete = completedSteps >= STEP_KEYS.length;

  useEffect(() => {
    if (isComplete) {
      return;
    }

    const timer = setTimeout(() => setCompletedSteps((count) => count + 1), STEP_DURATION_MS);

    return () => clearTimeout(timer);
  }, [completedSteps, isComplete]);

  useEffect(() => {
    Animated.timing(barProgress, {
      toValue: completedSteps / STEP_KEYS.length,
      duration: motion.slow,
      useNativeDriver: false,
    }).start();
  }, [barProgress, completedSteps]);

  const stateFor = (index: number): ProcessingStepState => {
    if (index < completedSteps) {
      return 'done';
    }

    return index === completedSteps ? 'active' : 'pending';
  };

  const width = barProgress.interpolate({
    inputRange: [0, 1],
    outputRange: ['0%', '100%'],
  });

  return (
    <ScreenContainer>
      <AppHeader
        title={t('processing.title')}
        subtitle={t('processing.subtitle')}
        onBackPress={() => navigation.goBack()}
        backLabel={t('common.back')}
      />

      <View style={styles.progressTrack}>
        <Animated.View style={[styles.progressFill, { width }]} />
      </View>

      <Surface style={styles.steps}>
        {STEP_KEYS.map((key, index) => (
          <ProcessingStepRow key={key} label={t(key)} state={stateFor(index)} />
        ))}
      </Surface>

      {isComplete && (
        <Surface style={styles.completeCard}>
          <Text style={styles.completeTitle}>{t('processing.completeTitle')}</Text>
          <Text style={styles.completeDescription}>{t('processing.completeDescription')}</Text>
          <PrimaryButton
            label={t('processing.viewEvidence')}
            icon="document-text-outline"
            onPress={() => navigation.replace('Evidence', { inspectionId })}
            fullWidth
            style={styles.completeButton}
          />
        </Surface>
      )}
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  progressTrack: {
    height: 6,
    borderRadius: radii.pill,
    backgroundColor: colors.surfaceMuted,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: radii.pill,
    backgroundColor: colors.primary,
  },
  steps: {
    marginTop: spacing.xl,
    paddingVertical: spacing.sm,
  },
  completeCard: {
    marginTop: spacing.xl,
  },
  completeTitle: {
    ...typography.sectionTitle,
    color: colors.textPrimary,
  },
  completeDescription: {
    ...typography.body,
    color: colors.textSecondary,
    marginTop: spacing.xs,
  },
  completeButton: {
    marginTop: spacing.lg,
  },
});
