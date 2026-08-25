import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { colors, radii, spacing, typography } from '../theme';
import { Inspection } from '../types/inspection';

interface DataSourceNoticeProps {
  inspection: Inspection;
}

/**
 * A compact honesty banner shown at the top of result-related screens:
 *   - a DEMO or REAL (API) chip so a bundled sample is never mistaken for a live scan;
 *   - any advisory `notices` (i18n keys) about partial data — e.g. the legal stage
 *     was not available — stated plainly, never as an error or a verdict;
 *   - raw backend `warnings`, shown as-is.
 *
 * A demo record with no notices/warnings still shows the DEMO chip; a clean live
 * scan shows the API chip alone.
 */
export function DataSourceNotice({ inspection }: DataSourceNoticeProps) {
  const { t } = useTranslation();
  const isDemo = (inspection.source ?? 'DEMO') === 'DEMO';
  const notices = inspection.notices ?? [];
  const warnings = inspection.warnings ?? [];

  return (
    <View style={styles.wrap}>
      <View style={styles.chipRow}>
        <View style={[styles.chip, isDemo ? styles.chipDemo : styles.chipApi]}>
          <Ionicons
            name={isDemo ? 'flask-outline' : 'cloud-done-outline'}
            size={13}
            color={isDemo ? colors.warning : colors.success}
          />
          <Text style={[styles.chipText, { color: isDemo ? colors.warning : colors.success }]}>
            {isDemo ? t('live.demoBadge') : t('live.apiBadge')}
          </Text>
        </View>
        <Text style={styles.chipNote}>{isDemo ? t('live.demoNote') : t('live.apiNote')}</Text>
      </View>

      {(notices.length > 0 || warnings.length > 0) && (
        <View style={styles.notices}>
          {notices.map((key) => (
            <View key={key} style={styles.noticeRow}>
              <Ionicons name="information-circle-outline" size={14} color={colors.info} />
              <Text style={styles.noticeText}>{t(key)}</Text>
            </View>
          ))}
          {warnings.map((warning, index) => (
            <View key={`warn-${index}`} style={styles.noticeRow}>
              <Ionicons name="alert-circle-outline" size={14} color={colors.textMuted} />
              <Text style={styles.noticeText}>{warning}</Text>
            </View>
          ))}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    gap: spacing.sm,
    marginBottom: spacing.lg,
  },
  chipRow: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
    borderRadius: radii.sm,
    borderWidth: 1,
  },
  chipDemo: {
    backgroundColor: colors.warningSoft,
    borderColor: colors.warningBorder,
  },
  chipApi: {
    backgroundColor: colors.successSoft,
    borderColor: colors.successBorder,
  },
  chipText: {
    ...typography.label,
    fontSize: 11,
  },
  chipNote: {
    ...typography.caption,
    fontWeight: '400',
    color: colors.textMuted,
    flexShrink: 1,
  },
  notices: {
    gap: spacing.xs,
  },
  noticeRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.xs,
  },
  noticeText: {
    flex: 1,
    ...typography.caption,
    fontWeight: '400',
    color: colors.textSecondary,
  },
});
