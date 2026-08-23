import { Ionicons } from '@expo/vector-icons';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { AppHeader } from '../components/AppHeader';
import { ComplianceCard } from '../components/ComplianceCard';
import { EmptyState } from '../components/EmptyState';
import { FadeIn } from '../components/FadeIn';
import { HeroScanCard } from '../components/HeroScanCard';
import { InspectionCard } from '../components/InspectionCard';
import { IntelligenceTile } from '../components/IntelligenceTile';
import { QuickActionCard } from '../components/QuickActionCard';
import { ScreenContainer } from '../components/ScreenContainer';
import { SectionHeader } from '../components/SectionHeader';
import { StatCard } from '../components/StatCard';
import { mockInspections, mockMandatoryDeclarations } from '../data/mockInspections';
import { mockInspectionSummary } from '../data/mockStatistics';
import { TabScreenProps } from '../navigation/types';
import { colors, spacing, typography } from '../theme';

const RECENT_LIMIT = 3;

const intelligenceOptions: Array<{
  labelKey: string;
  descriptionKey: string;
  icon: keyof typeof Ionicons.glyphMap;
}> = [
  { labelKey: 'home.nutrition', descriptionKey: 'comingSoon.nutrition', icon: 'nutrition-outline' },
  { labelKey: 'home.ingredients', descriptionKey: 'comingSoon.ingredients', icon: 'flask-outline' },
  {
    labelKey: 'home.labelInformation',
    descriptionKey: 'comingSoon.labelInformation',
    icon: 'pricetag-outline',
  },
];

function greetingKey(hour: number): string {
  if (hour < 12) {
    return 'greeting.morning';
  }

  return hour < 17 ? 'greeting.afternoon' : 'greeting.evening';
}

export function HomeScreen({ navigation }: TabScreenProps<'Home'>) {
  const { t } = useTranslation();
  const recentInspections = mockInspections.slice(0, RECENT_LIMIT);

  const openPlaceholder = (title: string, description: string) =>
    navigation.navigate('ComingSoon', { title, description });

  return (
    <ScreenContainer>
      <AppHeader
        greeting={t(greetingKey(new Date().getHours()))}
        title={t('common.appName')}
        subtitle={t('common.tagline')}
        showBrandMark
        actionIcon="person-circle-outline"
        actionLabel={t('nav.profile')}
        onActionPress={() => navigation.navigate('Profile')}
      />

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent}>
        <FadeIn>
          <HeroScanCard onScanPress={() => navigation.navigate('Scan')} />
        </FadeIn>

        <FadeIn delay={60} style={styles.section}>
          <View style={styles.quickActions}>
            <QuickActionCard
              label={t('home.quickScan')}
              icon="scan-outline"
              onPress={() => navigation.navigate('Scan')}
            />
            <QuickActionCard
              label={t('home.uploadImage')}
              icon="cloud-upload-outline"
              onPress={() => openPlaceholder(t('home.uploadImage'), t('comingSoon.uploadImage'))}
            />
            <QuickActionCard
              label={t('home.inspectionHistory')}
              icon="time-outline"
              onPress={() => navigation.navigate('History')}
            />
          </View>
        </FadeIn>

        <FadeIn delay={120} style={styles.section}>
          <ComplianceCard declarationKeys={mockMandatoryDeclarations} />
        </FadeIn>

        <FadeIn delay={180} style={styles.section}>
          <SectionHeader
            title={t('home.statisticsTitle')}
            description={t('home.statisticsSubtitle')}
          />
          <View style={styles.statsRow}>
            <StatCard value={mockInspectionSummary.total} label={t('home.statInspections')} />
            <StatCard
              value={mockInspectionSummary.compliant}
              label={t('home.statPassed')}
              tint={colors.success}
            />
            <StatCard
              value={mockInspectionSummary.manualReview}
              label={t('home.statReview')}
              tint={colors.info}
            />
            <StatCard
              value={mockInspectionSummary.potentialIssues}
              label={t('home.statIssue')}
              tint={colors.warning}
            />
          </View>
        </FadeIn>

        <FadeIn delay={240} style={styles.section}>
          <SectionHeader
            title={t('home.recentTitle')}
            actionLabel={t('common.viewAll')}
            onActionPress={() => navigation.navigate('History')}
          />
          {recentInspections.length === 0 ? (
            <EmptyState
              icon="document-outline"
              title={t('home.emptyRecentTitle')}
              description={t('home.emptyRecentDescription')}
            />
          ) : (
            <View style={styles.inspectionList}>
              {recentInspections.map((inspection) => (
                <InspectionCard
                  key={inspection.id}
                  inspection={inspection}
                  onPress={() => navigation.navigate('Evidence', { inspectionId: inspection.id })}
                />
              ))}
            </View>
          )}
        </FadeIn>

        <FadeIn delay={300} style={styles.section}>
          <SectionHeader title={t('home.intelligenceTitle')} />
          <View style={styles.intelligenceRow}>
            {intelligenceOptions.map((option) => (
              <IntelligenceTile
                key={option.labelKey}
                label={t(option.labelKey)}
                icon={option.icon}
                onPress={() => openPlaceholder(t(option.labelKey), t(option.descriptionKey))}
              />
            ))}
          </View>
        </FadeIn>

        <Text style={styles.disclaimer}>{t('common.sampleData')}</Text>
      </ScrollView>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  scrollContent: {
    paddingBottom: spacing.xxxl,
  },
  section: {
    marginTop: spacing.xxl,
  },
  quickActions: {
    flexDirection: 'row',
    gap: spacing.md,
  },
  /** Wraps to two rows rather than overflowing on narrow devices. */
  statsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  inspectionList: {
    gap: spacing.md,
  },
  intelligenceRow: {
    flexDirection: 'row',
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
