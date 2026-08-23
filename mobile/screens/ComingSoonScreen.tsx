import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { AppHeader } from '../components/AppHeader';
import { PrimaryButton } from '../components/PrimaryButton';
import { ScreenContainer } from '../components/ScreenContainer';
import { ComingSoonScreenProps } from '../navigation/types';
import { colors, radii, spacing, typography } from '../theme';

/**
 * Shared destination for features that are planned but not part of this UI iteration.
 */
export function ComingSoonScreen({ navigation, route }: ComingSoonScreenProps) {
  const { t } = useTranslation();
  const { title, description } = route.params;

  return (
    <ScreenContainer>
      <AppHeader title="" onBackPress={() => navigation.goBack()} backLabel={t('common.back')} />

      <View style={styles.content}>
        <View style={styles.iconWrap}>
          <Ionicons name="construct-outline" size={26} color={colors.primary} />
        </View>
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.description}>{description}</Text>
        <PrimaryButton
          label={t('common.backToHome')}
          variant="outline"
          onPress={() => navigation.goBack()}
          style={styles.button}
        />
      </View>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  content: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingBottom: spacing.xxxl,
  },
  iconWrap: {
    width: 56,
    height: 56,
    borderRadius: radii.lg,
    backgroundColor: colors.primarySoft,
    borderWidth: 1,
    borderColor: colors.primaryBorder,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.xl,
  },
  title: {
    ...typography.screenTitle,
    color: colors.textPrimary,
    textAlign: 'center',
  },
  description: {
    ...typography.body,
    color: colors.textSecondary,
    textAlign: 'center',
    marginTop: spacing.sm,
  },
  button: {
    marginTop: spacing.xxl,
  },
});
