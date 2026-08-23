import { useEffect, useRef } from 'react';
import { Animated, StyleSheet, Text } from 'react-native';
import { useTranslation } from 'react-i18next';

import { STATUS_PRESENTATION } from '../constants/compliance';
import { motion, radii, spacing, typography } from '../theme';
import { ComplianceStatus } from '../types/inspection';

interface StatusBadgeProps {
  status: ComplianceStatus;
  /** Uses the shorter sentence-case label instead of the full chip wording. */
  compact?: boolean;
}

export function StatusBadge({ status, compact = false }: StatusBadgeProps) {
  const { t } = useTranslation();
  const presentation = STATUS_PRESENTATION[status];
  const opacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(opacity, {
      toValue: 1,
      duration: motion.base,
      useNativeDriver: true,
    }).start();
  }, [opacity]);

  const label = t(compact ? presentation.labelKey : presentation.badgeKey);

  return (
    <Animated.View
      accessibilityLabel={t(presentation.labelKey)}
      style={[
        styles.badge,
        { opacity, backgroundColor: presentation.softBackground, borderColor: presentation.border },
      ]}
    >
      <Text style={[styles.glyph, { color: presentation.tint }]}>{presentation.glyph}</Text>
      <Text style={[styles.label, { color: presentation.tint }]} numberOfLines={1}>
        {label}
      </Text>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    gap: spacing.xs,
    paddingHorizontal: spacing.sm,
    paddingVertical: 5,
    borderRadius: radii.sm,
    borderWidth: 1,
  },
  glyph: {
    fontSize: 12,
    lineHeight: 14,
    fontWeight: '700',
  },
  label: {
    ...typography.label,
  },
});
