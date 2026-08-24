import { Ionicons } from '@expo/vector-icons';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { AppHeader } from '../components/AppHeader';
import { DeclaredObservedRow } from '../components/DeclaredObservedRow';
import { EmptyState } from '../components/EmptyState';
import { FadeIn } from '../components/FadeIn';
import { ScreenContainer } from '../components/ScreenContainer';
import { Surface } from '../components/Surface';
import { VerificationStatusBadge } from '../components/VerificationStatusBadge';
import { VERIFICATION_PRESENTATION } from '../constants/verification';
import { findMockInspection } from '../data/mockInspections';
import { VerificationScreenProps } from '../navigation/types';
import { colors, radii, spacing, typography } from '../theme';
import { formatConfidence } from '../utils/formatConfidence';

export function VerificationScreen({ navigation, route }: VerificationScreenProps) {
  const { t } = useTranslation();
  const inspection = findMockInspection(route.params.inspectionId);
  const verification = inspection?.verification;

  if (!inspection || !verification || verification.checks.length === 0) {
    return (
      <ScreenContainer>
        <AppHeader
          title={t('verification.title')}
          subtitle={t('verification.subtitle')}
          onBackPress={() => navigation.goBack()}
          backLabel={t('common.back')}
        />
        <EmptyState
          icon="help-circle-outline"
          title={t('verification.emptyTitle')}
          description={t('verification.emptyDescription')}
        />
      </ScreenContainer>
    );
  }

  const presentation = VERIFICATION_PRESENTATION[verification.status];
  const hasMeasurement = verification.checks.some((check) => check.method === 'USER_MEASUREMENT');

  return (
    <ScreenContainer>
      <AppHeader
        title={t('verification.title')}
        subtitle={inspection.productName}
        onBackPress={() => navigation.goBack()}
        backLabel={t('common.back')}
      />

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent}>
        <FadeIn>
          <Surface>
            <View style={styles.header}>
              <Text style={styles.overallLabel}>{t('verification.overallStatus')}</Text>
              <VerificationStatusBadge status={verification.status} />
            </View>
            <Text style={styles.helper}>{t(presentation.helperKey)}</Text>

            <View style={styles.confidencePill}>
              <Ionicons name="stats-chart-outline" size={14} color={colors.textSecondary} />
              <Text style={styles.confidenceText}>
                {t('verification.confidence')}: {formatConfidence(verification.confidence)}
              </Text>
            </View>

            <Text style={styles.explanation}>{t('verification.explanation')}</Text>
          </Surface>
        </FadeIn>

        {hasMeasurement && (
          <FadeIn delay={60} style={styles.section}>
            <View style={styles.massNotice}>
              <Ionicons name="information-circle-outline" size={16} color={colors.info} />
              <Text style={styles.massNoticeText}>{t('verification.massNotice')}</Text>
            </View>
          </FadeIn>
        )}

        {verification.checks.map((check, index) => {
          const evidenceItem = check.evidenceId
            ? inspection.evidence?.find((item) => item.id === check.evidenceId)
            : undefined;

          return (
            <FadeIn key={check.id} delay={120 + index * 60} style={styles.section}>
              <DeclaredObservedRow
                check={check}
                onEvidencePress={
                  evidenceItem
                    ? () => navigation.navigate('EvidenceDetail', { item: evidenceItem })
                    : undefined
                }
              />
            </FadeIn>
          );
        })}
      </ScrollView>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  scrollContent: {
    paddingBottom: spacing.xxxl,
  },
  section: {
    marginTop: spacing.lg,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.md,
  },
  overallLabel: {
    ...typography.sectionTitle,
    color: colors.textPrimary,
  },
  helper: {
    ...typography.body,
    color: colors.textSecondary,
    marginTop: spacing.sm,
  },
  confidencePill: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    gap: spacing.xs,
    marginTop: spacing.md,
    paddingHorizontal: spacing.sm,
    paddingVertical: 5,
    borderRadius: radii.sm,
    backgroundColor: colors.surfaceMuted,
    borderWidth: 1,
    borderColor: colors.border,
  },
  confidenceText: {
    ...typography.caption,
    color: colors.textSecondary,
  },
  explanation: {
    ...typography.caption,
    fontWeight: '400',
    color: colors.textMuted,
    marginTop: spacing.md,
  },
  massNotice: {
    flexDirection: 'row',
    gap: spacing.sm,
    padding: spacing.md,
    borderRadius: radii.md,
    backgroundColor: colors.infoSoft,
    borderWidth: 1,
    borderColor: colors.infoBorder,
  },
  massNoticeText: {
    flex: 1,
    ...typography.caption,
    fontWeight: '400',
    color: colors.textSecondary,
  },
});
