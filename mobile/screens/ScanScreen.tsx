import { Ionicons } from '@expo/vector-icons';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { AppHeader } from '../components/AppHeader';
import { PrimaryButton } from '../components/PrimaryButton';
import { ScreenContainer } from '../components/ScreenContainer';
import { Surface } from '../components/Surface';
import { mockInspections } from '../data/mockInspections';
import { TabScreenProps } from '../navigation/types';
import { colors, radii, spacing, typography } from '../theme';

const CHECKLIST_KEYS = [
  'scan.clearlyVisible',
  'scan.wellLit',
  'scan.notBlurry',
  'scan.insideFrame',
];

export function ScanScreen({ navigation }: TabScreenProps<'Scan'>) {
  const { t } = useTranslation();

  /** The pipeline is simulated, so it replays the first sample record. */
  const sampleInspectionId = mockInspections[0].id;

  return (
    <ScreenContainer>
      <AppHeader title={t('scan.title')} subtitle={t('scan.subtitle')} />

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent}>
        <View style={styles.preview} accessibilityLabel={t('scan.placeholderTitle')}>
          <View style={[styles.corner, styles.cornerTopLeft]} />
          <View style={[styles.corner, styles.cornerTopRight]} />
          <View style={[styles.corner, styles.cornerBottomLeft]} />
          <View style={[styles.corner, styles.cornerBottomRight]} />

          <Ionicons name="camera-outline" size={38} color={colors.textInverseMuted} />
          <Text style={styles.previewTitle}>{t('scan.placeholderTitle')}</Text>
          <Text style={styles.previewHint}>{t('scan.placeholderHint')}</Text>
        </View>

        <Surface style={styles.checklistCard}>
          <Text style={styles.checklistTitle}>{t('scan.checklistTitle')}</Text>
          {CHECKLIST_KEYS.map((key) => (
            <View key={key} style={styles.checklistRow}>
              <Text style={styles.checklistGlyph}>✓</Text>
              <Text style={styles.checklistText}>{t(key)}</Text>
            </View>
          ))}
        </Surface>

        <PrimaryButton
          label={t('scan.capture')}
          icon="scan-outline"
          onPress={() => navigation.navigate('Processing', { inspectionId: sampleInspectionId })}
          fullWidth
          style={styles.captureButton}
        />
        <Text style={styles.footnote}>{t('scan.footnote')}</Text>
      </ScrollView>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  scrollContent: {
    paddingBottom: spacing.xxxl,
  },
  preview: {
    width: '100%',
    aspectRatio: 3 / 4,
    maxHeight: 420,
    borderRadius: radii.xl,
    backgroundColor: colors.primaryDeep,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
    padding: spacing.xxl,
    overflow: 'hidden',
  },
  corner: {
    position: 'absolute',
    width: 34,
    height: 34,
    borderColor: colors.textInverseMuted,
  },
  cornerTopLeft: {
    top: spacing.xl,
    left: spacing.xl,
    borderTopWidth: 2,
    borderLeftWidth: 2,
    borderTopLeftRadius: radii.sm,
  },
  cornerTopRight: {
    top: spacing.xl,
    right: spacing.xl,
    borderTopWidth: 2,
    borderRightWidth: 2,
    borderTopRightRadius: radii.sm,
  },
  cornerBottomLeft: {
    bottom: spacing.xl,
    left: spacing.xl,
    borderBottomWidth: 2,
    borderLeftWidth: 2,
    borderBottomLeftRadius: radii.sm,
  },
  cornerBottomRight: {
    bottom: spacing.xl,
    right: spacing.xl,
    borderBottomWidth: 2,
    borderRightWidth: 2,
    borderBottomRightRadius: radii.sm,
  },
  previewTitle: {
    ...typography.cardTitle,
    color: colors.textInverse,
    marginTop: spacing.sm,
  },
  previewHint: {
    ...typography.caption,
    fontWeight: '400',
    color: colors.textInverseMuted,
    textAlign: 'center',
  },
  checklistCard: {
    marginTop: spacing.xl,
    gap: spacing.sm,
  },
  checklistTitle: {
    ...typography.cardTitle,
    color: colors.textPrimary,
    marginBottom: spacing.xs,
  },
  checklistRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  checklistGlyph: {
    fontSize: 13,
    lineHeight: 18,
    fontWeight: '700',
    color: colors.success,
  },
  checklistText: {
    ...typography.body,
    color: colors.textSecondary,
  },
  captureButton: {
    marginTop: spacing.xl,
  },
  footnote: {
    ...typography.caption,
    fontWeight: '400',
    color: colors.textMuted,
    textAlign: 'center',
    marginTop: spacing.md,
  },
});
