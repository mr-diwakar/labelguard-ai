import { Ionicons } from '@expo/vector-icons';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { AppHeader } from '../components/AppHeader';
import { DataSourceNotice } from '../components/DataSourceNotice';
import { EmptyState } from '../components/EmptyState';
import { FadeIn } from '../components/FadeIn';
import { LegalCheckList } from '../components/LegalCheckList';
import { NavRow } from '../components/NavRow';
import { PrimaryButton } from '../components/PrimaryButton';
import { ScreenContainer } from '../components/ScreenContainer';
import { SectionHeader } from '../components/SectionHeader';
import { StatusBadge } from '../components/StatusBadge';
import { Surface } from '../components/Surface';
import { VerificationStatusBadge } from '../components/VerificationStatusBadge';
import { VERIFICATION_PRESENTATION } from '../constants/verification';
import { DEFAULT_DEMO_KEY } from '../data/demoScans';
import { getDemoKeyFor, getInspection } from '../data/inspectionStore';
import { ResultScreenProps } from '../navigation/types';
import { colors, radii, spacing, typography } from '../theme';
import { VerificationOutcome } from '../types/inspection';
import { formatConfidence } from '../utils/formatConfidence';
import { formatRelativeDate } from '../utils/formatRelativeDate';

export function ResultScreen({ navigation, route }: ResultScreenProps) {
  const { t } = useTranslation();
  const inspection = getInspection(route.params.inspectionId);

  if (!inspection) {
    return (
      <ScreenContainer>
        <AppHeader
          title={t('result.title')}
          onBackPress={() => navigation.goBack()}
          backLabel={t('common.back')}
        />
        <EmptyState icon="document-outline" title={t('result.notFound')} />
      </ScreenContainer>
    );
  }

  const { assessment, verification } = inspection;

  const outcome: VerificationOutcome = verification?.status ?? 'COULD_NOT_VERIFY';
  const verificationPresentation = VERIFICATION_PRESENTATION[outcome];
  const headlineCheck =
    verification?.checks.find((check) => check.status === verification.status) ??
    verification?.checks[0];

  const evidenceCount = inspection.evidence?.length ?? 0;
  const subtitle = [formatRelativeDate(inspection.inspectedAt, t), inspection.category]
    .filter(Boolean)
    .join(' · ');

  const openPlaceholder = (title: string, description: string) =>
    navigation.navigate('ComingSoon', { title, description });

  return (
    <ScreenContainer>
      <AppHeader
        title={inspection.productName}
        subtitle={subtitle}
        onBackPress={() => navigation.goBack()}
        backLabel={t('common.back')}
      />

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent}>
        <DataSourceNotice inspection={inspection} />

        {/* Priority 1 — Legal Metrology label check. */}
        <FadeIn>
          <Surface>
            <View style={styles.cardHeader}>
              <View style={styles.cardHeaderTexts}>
                <Text style={styles.cardTitle}>{t('result.legalTitle')}</Text>
                <Text style={styles.cardDescription}>{t('result.legalDescription')}</Text>
              </View>
              <StatusBadge status={assessment.status} />
            </View>

            <View style={styles.legalList}>
              <LegalCheckList assessment={assessment} />
            </View>

            {assessment.ruleReference && (
              <Text style={styles.ruleReference}>{assessment.ruleReference}</Text>
            )}

            <View style={styles.notice}>
              <Ionicons name="information-circle-outline" size={16} color={colors.info} />
              <Text style={styles.noticeText}>{t('result.legalNotice')}</Text>
            </View>
          </Surface>
        </FadeIn>

        {/* Priority 2 — Label-to-product verification, with evidence entry points. */}
        <FadeIn delay={60} style={styles.section}>
          <Surface>
            <View style={styles.cardHeader}>
              <View style={styles.cardHeaderTexts}>
                <Text style={styles.cardTitle}>{t('result.verificationTitle')}</Text>
                <Text style={styles.cardDescription}>{t('result.verificationDescription')}</Text>
              </View>
              <VerificationStatusBadge status={outcome} />
            </View>

            <Text style={styles.helper}>{t(verificationPresentation.helperKey)}</Text>

            {headlineCheck && (
              <View style={styles.compareBlock}>
                <View style={styles.compareRow}>
                  <View style={styles.compareCol}>
                    <Text style={styles.compareLabel}>{t('result.declared')}</Text>
                    <Text style={styles.compareValue}>{headlineCheck.declared ?? '—'}</Text>
                  </View>
                  <Ionicons name="arrow-forward" size={16} color={colors.textMuted} style={styles.arrow} />
                  <View style={styles.compareCol}>
                    <Text style={styles.compareLabel}>{t('result.observed')}</Text>
                    <Text
                      style={[
                        styles.compareValue,
                        headlineCheck.observed === undefined && styles.compareValueMuted,
                      ]}
                    >
                      {headlineCheck.observed ?? t('verification.couldNotVerifyValue')}
                    </Text>
                  </View>
                </View>

                <View style={styles.metaRow}>
                  {headlineCheck.difference !== undefined && (
                    <Text style={styles.metaText}>
                      {t('result.difference')}: {headlineCheck.difference}
                    </Text>
                  )}
                  <Text style={styles.metaText}>
                    {t('result.confidence')}: {formatConfidence(verification?.confidence)}
                  </Text>
                </View>
              </View>
            )}

            <Pressable
              accessibilityRole="button"
              accessibilityLabel={t('result.whatVerified')}
              onPress={() => navigation.navigate('Verification', { inspectionId: inspection.id })}
              style={({ pressed }) => [styles.linkRow, pressed && styles.linkRowPressed]}
            >
              <Ionicons name="list-circle-outline" size={18} color={colors.primary} />
              <Text style={styles.linkText}>{t('result.whatVerified')}</Text>
              <Ionicons name="chevron-forward" size={16} color={colors.primary} />
            </Pressable>

            <View style={styles.actions}>
              <PrimaryButton
                label={t('result.viewEvidence')}
                icon="images-outline"
                onPress={() => navigation.navigate('Evidence', { inspectionId: inspection.id })}
                fullWidth
                style={styles.actionButton}
              />
              <PrimaryButton
                label={t('result.verifyAgain')}
                icon="refresh-outline"
                variant="outline"
                onPress={() =>
                  navigation.navigate('Processing', {
                    demoKey: getDemoKeyFor(inspection.id) ?? DEFAULT_DEMO_KEY,
                  })
                }
                fullWidth
                style={styles.actionButton}
              />
            </View>
          </Surface>
        </FadeIn>

        {/* Priorities 3–5 and planned sections. */}
        <FadeIn delay={120} style={styles.section}>
          <SectionHeader title={t('result.moreTitle')} />
          <View style={styles.navList}>
            <NavRow
              icon="images-outline"
              label={t('result.evidenceTitle')}
              description={t('result.evidenceHint')}
              tag={evidenceCount > 0 ? String(evidenceCount) : undefined}
              onPress={() => navigation.navigate('Evidence', { inspectionId: inspection.id })}
            />
            <NavRow
              icon="nutrition-outline"
              label={t('home.nutrition')}
              description={t('result.plannedHint')}
              tag={t('result.soon')}
              onPress={() => openPlaceholder(t('home.nutrition'), t('comingSoon.nutrition'))}
            />
            <NavRow
              icon="flask-outline"
              label={t('home.ingredients')}
              description={t('result.plannedHint')}
              tag={t('result.soon')}
              onPress={() => openPlaceholder(t('home.ingredients'), t('comingSoon.ingredients'))}
            />
            <NavRow
              icon="git-compare-outline"
              label={t('result.compare')}
              description={t('result.plannedHint')}
              tag={t('result.soon')}
              onPress={() => openPlaceholder(t('result.compare'), t('comingSoon.compare'))}
            />
            <NavRow
              icon="save-outline"
              label={t('result.report')}
              description={t('result.plannedHint')}
              tag={t('result.soon')}
              onPress={() => openPlaceholder(t('result.report'), t('comingSoon.report'))}
            />
          </View>
        </FadeIn>

        {/* The blanket "sample data" line applies only to bundled demo records;
            a real API result is labelled by the DataSourceNotice above instead. */}
        {(inspection.source ?? 'DEMO') === 'DEMO' && (
          <Text style={styles.disclaimer}>{t('common.sampleData')}</Text>
        )}
      </ScrollView>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  scrollContent: {
    paddingBottom: spacing.xxxl,
  },
  section: {
    marginTop: spacing.xl,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: spacing.md,
  },
  cardHeaderTexts: {
    flex: 1,
  },
  cardTitle: {
    ...typography.sectionTitle,
    color: colors.textPrimary,
  },
  cardDescription: {
    ...typography.body,
    color: colors.textSecondary,
    marginTop: spacing.xs,
  },
  legalList: {
    marginTop: spacing.lg,
  },
  ruleReference: {
    ...typography.caption,
    fontWeight: '400',
    color: colors.textMuted,
    marginTop: spacing.lg,
  },
  notice: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginTop: spacing.lg,
    padding: spacing.md,
    borderRadius: radii.md,
    backgroundColor: colors.infoSoft,
    borderWidth: 1,
    borderColor: colors.infoBorder,
  },
  noticeText: {
    flex: 1,
    ...typography.caption,
    fontWeight: '400',
    color: colors.textSecondary,
  },
  helper: {
    ...typography.body,
    color: colors.textSecondary,
    marginTop: spacing.sm,
  },
  compareBlock: {
    marginTop: spacing.lg,
    padding: spacing.lg,
    borderRadius: radii.md,
    backgroundColor: colors.surfaceMuted,
    gap: spacing.md,
  },
  compareRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  compareCol: {
    flex: 1,
    gap: 2,
  },
  arrow: {
    marginTop: spacing.md,
  },
  compareLabel: {
    ...typography.label,
    color: colors.textMuted,
  },
  compareValue: {
    ...typography.stat,
    fontSize: 20,
    lineHeight: 24,
    color: colors.textPrimary,
  },
  compareValueMuted: {
    ...typography.body,
    color: colors.textMuted,
  },
  metaRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
  },
  metaText: {
    ...typography.caption,
    fontWeight: '400',
    color: colors.textSecondary,
  },
  actions: {
    marginTop: spacing.lg,
    gap: spacing.md,
  },
  linkRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginTop: spacing.lg,
    paddingVertical: spacing.sm,
  },
  linkRowPressed: {
    opacity: 0.6,
  },
  linkText: {
    ...typography.cardTitle,
    color: colors.primary,
    flex: 1,
  },
  actionButton: {
    marginTop: 0,
  },
  navList: {
    gap: spacing.md,
  },
  disclaimer: {
    ...typography.caption,
    fontWeight: '400',
    color: colors.textMuted,
    textAlign: 'center',
    marginTop: spacing.xxl,
  },
});
