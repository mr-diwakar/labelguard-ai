import { Ionicons } from '@expo/vector-icons';
import { useMemo, useState } from 'react';
import { FlatList, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { AppHeader } from '../components/AppHeader';
import { EmptyState } from '../components/EmptyState';
import { InspectionCard } from '../components/InspectionCard';
import { ScreenContainer } from '../components/ScreenContainer';
import { STATUS_FILTERS, StatusFilterValue } from '../constants/compliance';
import { mockInspections } from '../data/mockInspections';
import { TabScreenProps } from '../navigation/types';
import { colors, radii, spacing, typography } from '../theme';

export function HistoryScreen({ navigation }: TabScreenProps<'History'>) {
  const { t } = useTranslation();
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilterValue>('ALL');

  const inspections = useMemo(() => {
    const search = query.trim().toLowerCase();

    return mockInspections.filter((inspection) => {
      const matchesStatus = statusFilter === 'ALL' || inspection.assessment.status === statusFilter;
      const matchesSearch =
        search.length === 0 || inspection.productName.toLowerCase().includes(search);

      return matchesStatus && matchesSearch;
    });
  }, [query, statusFilter]);

  return (
    <ScreenContainer>
      <AppHeader title={t('history.title')} subtitle={t('history.subtitle')} />

      <View style={styles.searchField}>
        <Ionicons name="search-outline" size={18} color={colors.textMuted} />
        <TextInput
          value={query}
          onChangeText={setQuery}
          placeholder={t('history.searchPlaceholder')}
          placeholderTextColor={colors.textMuted}
          style={styles.searchInput}
          accessibilityLabel={t('history.searchPlaceholder')}
          returnKeyType="search"
        />
        {query.length > 0 && (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={t('history.clearSearch')}
            onPress={() => setQuery('')}
            hitSlop={8}
          >
            <Ionicons name="close-circle" size={18} color={colors.textMuted} />
          </Pressable>
        )}
      </View>

      <View style={styles.filterRow}>
        {STATUS_FILTERS.map((filter) => {
          const isActive = filter.value === statusFilter;

          return (
            <Pressable
              key={filter.value}
              accessibilityRole="button"
              accessibilityState={{ selected: isActive }}
              onPress={() => setStatusFilter(filter.value)}
              style={[styles.filterChip, isActive && styles.filterChipActive]}
            >
              <Text style={[styles.filterLabel, isActive && styles.filterLabelActive]}>
                {t(filter.labelKey)}
              </Text>
            </Pressable>
          );
        })}
      </View>

      <FlatList
        data={inspections}
        keyExtractor={(item) => item.id}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.listContent}
        renderItem={({ item }) => (
          <InspectionCard
            inspection={item}
            onPress={() => navigation.navigate('Evidence', { inspectionId: item.id })}
          />
        )}
        ListEmptyComponent={
          <EmptyState
            icon="document-outline"
            title={t('history.emptyTitle')}
            description={t('history.emptyDescription')}
          />
        }
      />
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  searchField: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    minHeight: 48,
    paddingHorizontal: spacing.md,
    backgroundColor: colors.surface,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  searchInput: {
    flex: 1,
    ...typography.body,
    color: colors.textPrimary,
    paddingVertical: spacing.md,
  },
  filterRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    marginTop: spacing.md,
    marginBottom: spacing.lg,
  },
  filterChip: {
    minHeight: 36,
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderRadius: radii.pill,
    borderWidth: 1,
    borderColor: colors.primaryBorder,
    backgroundColor: colors.surface,
  },
  filterChipActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  filterLabel: {
    ...typography.caption,
    color: colors.primaryMuted,
  },
  filterLabelActive: {
    color: colors.textInverse,
  },
  listContent: {
    gap: spacing.md,
    paddingBottom: spacing.xxxl,
  },
});
