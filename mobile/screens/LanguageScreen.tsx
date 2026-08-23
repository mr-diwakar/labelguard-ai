import { ScrollView, StyleSheet, Text } from 'react-native';
import { useTranslation } from 'react-i18next';

import { AppHeader } from '../components/AppHeader';
import { LanguageSelector } from '../components/LanguageSelector';
import { ScreenContainer } from '../components/ScreenContainer';
import { LanguageScreenProps } from '../navigation/types';
import { colors, spacing, typography } from '../theme';

export function LanguageScreen({ navigation }: LanguageScreenProps) {
  const { t } = useTranslation();

  return (
    <ScreenContainer>
      <AppHeader
        title={t('language.title')}
        onBackPress={() => navigation.goBack()}
        backLabel={t('common.back')}
      />

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.content}>
        <Text style={styles.subtitle}>{t('language.subtitle')}</Text>
        <LanguageSelector />
      </ScrollView>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  content: {
    paddingBottom: spacing.xxxl,
  },
  subtitle: {
    ...typography.body,
    color: colors.textSecondary,
    marginBottom: spacing.lg,
  },
});
