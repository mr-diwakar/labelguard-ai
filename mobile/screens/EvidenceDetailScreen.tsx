import { Ionicons } from '@expo/vector-icons';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { AppHeader } from '../components/AppHeader';
import { FadeIn } from '../components/FadeIn';
import { ScreenContainer } from '../components/ScreenContainer';
import { Surface } from '../components/Surface';
import { EVIDENCE_TYPE_PRESENTATION } from '../constants/verification';
import { EvidenceDetailScreenProps } from '../navigation/types';
import { colors, radii, spacing, typography } from '../theme';
import { formatConfidence } from '../utils/formatConfidence';
import { formatRelativeDate } from '../utils/formatRelativeDate';

export function EvidenceDetailScreen({ navigation, route }: EvidenceDetailScreenProps) {
  const { t } = useTranslation();
  const { item } = route.params;
  const presentation = EVIDENCE_TYPE_PRESENTATION[item.type];
  const title = item.title ?? t(item.titleKey ?? presentation.labelKey);

  // A visual frame only makes sense for image-like evidence or anything that
  // carries a highlighted region; a note or a typed measurement shows as text.
  const hasVisual =
    item.type === 'PRODUCT_IMAGE' ||
    item.type === 'LABEL_IMAGE' ||
    item.type === 'HIGHLIGHTED_REGION' ||
    item.boundingBox !== undefined ||
    item.imageRef !== undefined;

  const details: Array<{ labelKey: string; value: string }> = [];
  if (item.expectedValue) {
    details.push({ labelKey: 'evidence.expectedValue', value: item.expectedValue });
  }
  if (item.observedValue) {
    details.push({ labelKey: 'evidence.observedValue', value: item.observedValue });
  }
  if (item.confidence !== undefined) {
    details.push({ labelKey: 'evidence.confidence', value: formatConfidence(item.confidence) });
  }
  details.push({ labelKey: 'evidence.capturedAt', value: formatRelativeDate(item.capturedAt, t) });

  return (
    <ScreenContainer>
      <AppHeader
        title={title}
        subtitle={t('evidence.detailSubtitle')}
        onBackPress={() => navigation.goBack()}
        backLabel={t('common.back')}
      />

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent}>
        {hasVisual && (
          <FadeIn>
            <View style={styles.imageFrame}>
              <Ionicons name={presentation.icon} size={30} color={colors.textInverseMuted} />
              <Text style={styles.imageCaption}>{t('evidence.imagePlaceholder')}</Text>

              {item.boundingBox && (
                <View
                  style={[
                    styles.bbox,
                    {
                      left: `${item.boundingBox.x * 100}%`,
                      top: `${item.boundingBox.y * 100}%`,
                      width: `${item.boundingBox.width * 100}%`,
                      height: `${item.boundingBox.height * 100}%`,
                    },
                  ]}
                />
              )}
            </View>

            {item.boundingBox && <Text style={styles.regionCaption}>{t('evidence.regionCaption')}</Text>}
          </FadeIn>
        )}

        <FadeIn delay={60} style={hasVisual ? styles.section : undefined}>
          <Surface>
            {details.map((row, index) => (
              <View
                key={row.labelKey}
                style={[styles.detailRow, index > 0 && styles.detailRowDivider]}
              >
                <Text style={styles.detailLabel}>{t(row.labelKey)}</Text>
                <Text style={styles.detailValue}>{row.value}</Text>
              </View>
            ))}

            {item.note && (
              <View style={styles.noteBlock}>
                <Text style={styles.detailLabel}>{t('evidence.noteLabel')}</Text>
                <Text style={styles.noteText}>{item.note}</Text>
              </View>
            )}
          </Surface>
        </FadeIn>

        {item.isPlaceholder && (
          <FadeIn delay={120} style={styles.section}>
            <View style={styles.notice}>
              <Ionicons name="image-outline" size={16} color={colors.textMuted} />
              <Text style={styles.noticeText}>{t('evidence.placeholderNotice')}</Text>
            </View>
          </FadeIn>
        )}

        <View style={styles.advisory}>
          <Ionicons name="shield-checkmark-outline" size={16} color={colors.textMuted} />
          <Text style={styles.advisoryText}>{t('evidence.detailAdvisory')}</Text>
        </View>
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
  imageFrame: {
    aspectRatio: 4 / 3,
    borderRadius: radii.lg,
    backgroundColor: colors.primaryDeep,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
    overflow: 'hidden',
  },
  imageCaption: {
    ...typography.caption,
    fontWeight: '400',
    color: colors.textInverseMuted,
  },
  bbox: {
    position: 'absolute',
    borderWidth: 2,
    borderColor: colors.warningBorder,
    borderRadius: radii.sm,
    backgroundColor: 'rgba(240, 213, 172, 0.18)',
  },
  regionCaption: {
    ...typography.caption,
    fontWeight: '400',
    color: colors.textMuted,
    marginTop: spacing.sm,
    paddingHorizontal: spacing.xs,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: spacing.lg,
    paddingVertical: spacing.md,
  },
  detailRowDivider: {
    borderTopWidth: 1,
    borderTopColor: colors.divider,
  },
  detailLabel: {
    ...typography.caption,
    color: colors.textMuted,
  },
  detailValue: {
    ...typography.cardTitle,
    color: colors.textPrimary,
    flexShrink: 1,
    textAlign: 'right',
  },
  noteBlock: {
    gap: spacing.xs,
    paddingTop: spacing.md,
    marginTop: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.divider,
  },
  noteText: {
    ...typography.body,
    color: colors.textSecondary,
  },
  notice: {
    flexDirection: 'row',
    gap: spacing.sm,
    padding: spacing.md,
    borderRadius: radii.md,
    backgroundColor: colors.surfaceMuted,
    borderWidth: 1,
    borderColor: colors.border,
  },
  noticeText: {
    flex: 1,
    ...typography.caption,
    fontWeight: '400',
    color: colors.textSecondary,
  },
  advisory: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginTop: spacing.xl,
    paddingHorizontal: spacing.xs,
  },
  advisoryText: {
    flex: 1,
    ...typography.caption,
    fontWeight: '400',
    color: colors.textMuted,
  },
});
