import { Ionicons } from '@expo/vector-icons';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { AppHeader } from '../components/AppHeader';
import { ScreenContainer } from '../components/ScreenContainer';
import { SectionHeader } from '../components/SectionHeader';
import { Surface } from '../components/Surface';
import { useAppLanguage } from '../hooks/useAppLanguage';
import { TabScreenProps } from '../navigation/types';
import { colors, radii, spacing, touchTarget, typography } from '../theme';

interface ProfileRow {
  labelKey: string;
  icon: keyof typeof Ionicons.glyphMap;
  descriptionKey?: string;
  value?: string;
  onPress: () => void;
}

export function ProfileScreen({ navigation }: TabScreenProps<'Profile'>) {
  const { t } = useTranslation();
  const { current } = useAppLanguage();

  const openPlaceholder = (labelKey: string, descriptionKey: string) =>
    navigation.navigate('ComingSoon', { title: t(labelKey), description: t(descriptionKey) });

  const preferenceRows: ProfileRow[] = [
    {
      labelKey: 'profile.language',
      icon: 'language-outline',
      value: current.nativeName,
      onPress: () => navigation.navigate('Language'),
    },
  ];

  const settingsRows: ProfileRow[] = [
    {
      labelKey: 'profile.notifications',
      icon: 'notifications-outline',
      onPress: () => openPlaceholder('profile.notifications', 'profile.notificationsDescription'),
    },
    {
      labelKey: 'profile.about',
      icon: 'information-circle-outline',
      onPress: () => openPlaceholder('profile.about', 'profile.aboutDescription'),
    },
  ];

  const renderRows = (rows: ProfileRow[]) => (
    <Surface padded={false}>
      {rows.map((row, index) => (
        <Pressable
          key={row.labelKey}
          accessibilityRole="button"
          accessibilityLabel={row.value ? `${t(row.labelKey)}, ${row.value}` : t(row.labelKey)}
          onPress={row.onPress}
          style={({ pressed }) => [
            styles.row,
            index > 0 && styles.rowDivided,
            pressed && styles.rowPressed,
          ]}
        >
          <Ionicons name={row.icon} size={20} color={colors.primaryMuted} />
          <Text style={styles.rowLabel}>{t(row.labelKey)}</Text>
          {row.value && <Text style={styles.rowValue}>{row.value}</Text>}
          <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
        </Pressable>
      ))}
    </Surface>
  );

  return (
    <ScreenContainer>
      <AppHeader title={t('profile.title')} />

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent}>
        <Surface style={styles.userCard}>
          <View style={styles.avatar}>
            <Ionicons name="person-outline" size={24} color={colors.textInverse} />
          </View>
          <View style={styles.userTexts}>
            <Text style={styles.userName}>{t('profile.userName')}</Text>
            <Text style={styles.userRole}>{t('profile.userRole')}</Text>
          </View>
        </Surface>

        <View style={styles.section}>
          <SectionHeader title={t('profile.preferences')} />
          {renderRows(preferenceRows)}
        </View>

        <View style={styles.section}>
          <SectionHeader title={t('profile.settings')} />
          {renderRows(settingsRows)}
        </View>

        <Text style={styles.footnote}>{t('profile.footnote')}</Text>
      </ScrollView>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  scrollContent: {
    paddingBottom: spacing.xxxl,
  },
  userCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.lg,
  },
  avatar: {
    width: 52,
    height: 52,
    borderRadius: radii.pill,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  userTexts: {
    flex: 1,
  },
  userName: {
    ...typography.sectionTitle,
    color: colors.textPrimary,
  },
  userRole: {
    ...typography.body,
    color: colors.textSecondary,
    marginTop: 2,
  },
  section: {
    marginTop: spacing.xxl,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    minHeight: touchTarget + 8,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
  },
  rowDivided: {
    borderTopWidth: 1,
    borderTopColor: colors.divider,
  },
  rowPressed: {
    backgroundColor: colors.surfaceMuted,
  },
  rowLabel: {
    flex: 1,
    ...typography.cardTitle,
    color: colors.textPrimary,
  },
  rowValue: {
    ...typography.body,
    color: colors.textSecondary,
  },
  footnote: {
    ...typography.caption,
    fontWeight: '400',
    color: colors.textMuted,
    textAlign: 'center',
    marginTop: spacing.xxl,
  },
});
