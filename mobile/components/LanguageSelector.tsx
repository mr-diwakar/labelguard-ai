import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { useAppLanguage } from '../hooks/useAppLanguage';
import { colors, radii, spacing, touchTarget, typography } from '../theme';
import { Surface } from './Surface';

export function LanguageSelector() {
  const { t } = useTranslation();
  const { languages, currentCode, changeLanguage } = useAppLanguage();

  return (
    <Surface padded={false}>
      {languages.map((language, index) => {
        const isSelected = language.code === currentCode;

        return (
          <Pressable
            key={language.code}
            accessibilityRole="radio"
            accessibilityState={{ selected: isSelected }}
            accessibilityLabel={`${language.nativeName}, ${language.englishName}`}
            onPress={() => changeLanguage(language.code)}
            style={({ pressed }) => [
              styles.row,
              index > 0 && styles.divided,
              pressed && styles.pressed,
            ]}
          >
            <View style={styles.texts}>
              <Text style={styles.nativeName}>{language.nativeName}</Text>
              <Text style={styles.englishName}>{language.englishName}</Text>
            </View>

            {isSelected ? (
              <View style={styles.selectedWrap}>
                <Ionicons name="checkmark" size={16} color={colors.textInverse} />
                <Text style={styles.selectedLabel}>{t('language.selected')}</Text>
              </View>
            ) : (
              <View style={styles.radio} />
            )}
          </Pressable>
        );
      })}
    </Surface>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.md,
    minHeight: touchTarget + 12,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
  },
  divided: {
    borderTopWidth: 1,
    borderTopColor: colors.divider,
  },
  pressed: {
    backgroundColor: colors.surfaceMuted,
  },
  texts: {
    flex: 1,
  },
  nativeName: {
    ...typography.cardTitle,
    fontSize: 16,
    color: colors.textPrimary,
  },
  englishName: {
    ...typography.caption,
    fontWeight: '400',
    color: colors.textMuted,
    marginTop: 2,
  },
  selectedWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    paddingHorizontal: spacing.sm,
    paddingVertical: 6,
    borderRadius: radii.sm,
    backgroundColor: colors.primary,
  },
  selectedLabel: {
    ...typography.label,
    color: colors.textInverse,
  },
  radio: {
    width: 20,
    height: 20,
    borderRadius: radii.pill,
    borderWidth: 2,
    borderColor: colors.primaryBorder,
  },
});
