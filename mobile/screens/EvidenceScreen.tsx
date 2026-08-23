import { Ionicons } from '@expo/vector-icons';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { AppHeader } from '../components/AppHeader';
import { EmptyState } from '../components/EmptyState';
import { FadeIn } from '../components/FadeIn';
import { ScreenContainer } from '../components/ScreenContainer';
import { SectionHeader } from '../components/SectionHeader';
import { StatusBadge } from '../components/StatusBadge';
import { Surface } from '../components/Surface';
import { STATUS_PRESENTATION } from '../constants/compliance';
import { findMockInspection } from '../data/mockInspections';
import { EvidenceScreenProps } from '../navigation/types';
import { colors, radii, spacing, typography } from '../theme';
import { DeclarationCheck } from '../types/inspection';

function toPercent(confidence?: number): string {
  return confidence === undefined ? '—' : `${Math.round(confidence * 100)}%`;
}

interface CheckListProps {
  title: string;
  checks: DeclarationCheck[];
  emptyLabel: string;
  tint: string;
  glyph: string;
}

function CheckList({ title, checks, emptyLabel, tint, glyph }: CheckListProps) {
  const { t } = useTranslation();

  return (
    <View style={styles.section}>
      <SectionHeader title={title} />
      <Surface padded={false}>
        {checks.length === 0 ? (
          <Text style={styles.emptyLabel}>{emptyLabel}</Text>
        ) : (
          checks.map((check, index) => (
            <View
              key={`${check.declarationKey}-${index}`}
              style={[styles.checkRow, index > 0 && styles.divided]}
            >
              <Text style={[styles.checkGlyph, { color: tint }]}>{glyph}</Text>
              <View style={styles.checkTexts}>
                <Text style={styles.checkLabel}>{t(check.declarationKey)}</Text>
                {check.note && <Text style={styles.checkNote}>{check.note}</Text>}
              </View>
              <Text style={styles.checkConfidence}>{toPercent(check.confidence)}</Text>
            </View>
          ))
        )}
      </Surface>
    </View>
  );
}

export function EvidenceScreen({ navigation, route }: EvidenceScreenProps) {
  const { t } = useTranslation();
  const inspection = findMockInspection(route.params.inspectionId);

  if (!inspection) {
    return (
      <ScreenContainer>
        <AppHeader
          title={t('evidence.title')}
          onBackPress={() => navigation.goBack()}
          backLabel={t('common.back')}
        />
        <EmptyState icon="document-outline" title={t('history.emptyTitle')} />
      </ScreenContainer>
    );
  }

  const { assessment } = inspection;
  const presentation = STATUS_PRESENTATION[assessment.status];
  const highlighted = assessment.violations[0]?.boundingBox ?? assessment.manualReview[0]?.boundingBox;

  return (
    <ScreenContainer>
      <AppHeader
        title={inspection.productName}
        subtitle={t('evidence.subtitle')}
        onBackPress={() => navigation.goBack()}
        backLabel={t('common.back')}
      />

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent}>
        <FadeIn>
          <View style={styles.imageFrame}>
            <Ionicons name="image-outline" size={30} color={colors.textInverseMuted} />
            <Text style={styles.imageLabel}>{t('evidence.imagePlaceholder')}</Text>

            {highlighted && (
              <View
                style={[
                  styles.boundingBox,
                  {
                    left: `${highlighted.x * 100}%`,
                    top: `${highlighted.y * 100}%`,
                    width: `${highlighted.width * 100}%`,
                    height: `${highlighted.height * 100}%`,
                    borderColor: presentation.tint,
                  },
                ]}
              >
                <View style={[styles.boundingLabel, { backgroundColor: presentation.tint }]}>
                  <Text style={styles.boundingLabelText}>{t('evidence.boundingBox')}</Text>
                </View>
              </View>
            )}
          </View>
        </FadeIn>

        <FadeIn delay={60} style={styles.section}>
          <Surface>
            <StatusBadge status={assessment.status} />
            <Text style={styles.helper}>{t(presentation.helperKey)}</Text>

            <View style={styles.metaGrid}>
              <View style={styles.metaItem}>
                <Text style={styles.metaLabel}>{t('evidence.confidence')}</Text>
                <Text style={styles.metaValue}>{toPercent(assessment.confidence)}</Text>
              </View>
              {assessment.ruleReference && (
                <View style={styles.metaItem}>
                  <Text style={styles.metaLabel}>{t('evidence.ruleReference')}</Text>
                  <Text style={styles.metaReference}>{assessment.ruleReference}</Text>
                </View>
              )}
            </View>

            <View style={styles.notice}>
              <Ionicons name="information-circle-outline" size={16} color={colors.info} />
              <Text style={styles.noticeText}>{t('evidence.manualMessage')}</Text>
            </View>
          </Surface>
        </FadeIn>

        <FadeIn delay={120}>
          <CheckList
            title={t('evidence.violationsTitle')}
            checks={assessment.violations}
            emptyLabel={t('evidence.emptyViolations')}
            tint={colors.warning}
            glyph="⚠"
          />
        </FadeIn>

        <FadeIn delay={180}>
          <CheckList
            title={t('evidence.reviewTitle')}
            checks={assessment.manualReview}
            emptyLabel={t('evidence.emptyReview')}
            tint={colors.info}
            glyph="?"
          />
        </FadeIn>

        <FadeIn delay={240}>
          <CheckList
            title={t('evidence.passedTitle')}
            checks={assessment.passed}
            emptyLabel={t('evidence.emptyPassed')}
            tint={colors.success}
            glyph="✓"
          />
        </FadeIn>
      </ScrollView>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  scrollContent: {
    paddingBottom: spacing.xxxl,
  },
  imageFrame: {
    width: '100%',
    aspectRatio: 4 / 3,
    borderRadius: radii.xl,
    backgroundColor: colors.primaryDeep,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
    overflow: 'hidden',
  },
  imageLabel: {
    ...typography.caption,
    fontWeight: '400',
    color: colors.textInverseMuted,
  },
  boundingBox: {
    position: 'absolute',
    borderWidth: 2,
    borderRadius: radii.sm,
  },
  boundingLabel: {
    position: 'absolute',
    top: -20,
    left: -2,
    paddingHorizontal: spacing.xs,
    paddingVertical: 2,
    borderRadius: radii.sm,
  },
  boundingLabelText: {
    ...typography.label,
    fontSize: 9,
    color: colors.textInverse,
  },
  section: {
    marginTop: spacing.xl,
  },
  helper: {
    ...typography.body,
    color: colors.textSecondary,
    marginTop: spacing.sm,
  },
  metaGrid: {
    gap: spacing.md,
    marginTop: spacing.lg,
  },
  metaItem: {
    gap: 2,
  },
  metaLabel: {
    ...typography.label,
    color: colors.textMuted,
  },
  metaValue: {
    ...typography.stat,
    fontSize: 20,
    lineHeight: 24,
    color: colors.textPrimary,
  },
  metaReference: {
    ...typography.body,
    color: colors.textPrimary,
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
  checkRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
  },
  divided: {
    borderTopWidth: 1,
    borderTopColor: colors.divider,
  },
  checkGlyph: {
    fontSize: 14,
    lineHeight: 18,
    fontWeight: '700',
  },
  checkTexts: {
    flex: 1,
  },
  checkLabel: {
    ...typography.cardTitle,
    color: colors.textPrimary,
  },
  checkNote: {
    ...typography.caption,
    fontWeight: '400',
    color: colors.textMuted,
    marginTop: 2,
  },
  checkConfidence: {
    ...typography.caption,
    color: colors.textSecondary,
  },
  emptyLabel: {
    ...typography.body,
    color: colors.textMuted,
    padding: spacing.lg,
  },
});
