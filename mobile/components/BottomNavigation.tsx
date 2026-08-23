import { Ionicons } from '@expo/vector-icons';
import { BottomTabBarProps } from '@react-navigation/bottom-tabs';
import { useEffect, useRef } from 'react';
import { Animated, Pressable, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { MainTabParamList } from '../navigation/types';
import { colors, motion, radii, shadows, spacing, typography } from '../theme';

interface TabMeta {
  labelKey: string;
  icon: keyof typeof Ionicons.glyphMap;
  activeIcon: keyof typeof Ionicons.glyphMap;
  /** Scanning is the core action, so its tab is filled rather than outlined. */
  emphasized?: boolean;
}

const TAB_META: Record<keyof MainTabParamList, TabMeta> = {
  Home: { labelKey: 'nav.home', icon: 'home-outline', activeIcon: 'home' },
  Scan: { labelKey: 'nav.scan', icon: 'scan-outline', activeIcon: 'scan', emphasized: true },
  History: { labelKey: 'nav.history', icon: 'time-outline', activeIcon: 'time' },
  Profile: { labelKey: 'nav.profile', icon: 'person-outline', activeIcon: 'person' },
};

interface TabButtonProps {
  meta: TabMeta;
  label: string;
  isFocused: boolean;
  onPress: () => void;
}

function TabButton({ meta, label, isFocused, onPress }: TabButtonProps) {
  const focus = useRef(new Animated.Value(isFocused ? 1 : 0)).current;

  useEffect(() => {
    Animated.timing(focus, {
      toValue: isFocused ? 1 : 0,
      duration: motion.base,
      useNativeDriver: true,
    }).start();
  }, [focus, isFocused]);

  const scale = focus.interpolate({ inputRange: [0, 1], outputRange: [1, 1.12] });

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected: isFocused }}
      accessibilityLabel={label}
      onPress={onPress}
      style={styles.tab}
    >
      <Animated.View
        style={[
          styles.iconSlot,
          meta.emphasized && styles.emphasizedIcon,
          meta.emphasized && isFocused && styles.emphasizedIconActive,
          { transform: [{ scale }] },
        ]}
      >
        <Ionicons
          name={isFocused || meta.emphasized ? meta.activeIcon : meta.icon}
          size={meta.emphasized ? 24 : 22}
          color={
            meta.emphasized
              ? colors.textInverse
              : isFocused
                ? colors.primary
                : colors.textMuted
          }
        />
      </Animated.View>

      <Text
        style={[
          styles.label,
          isFocused && styles.labelActive,
          meta.emphasized && styles.labelEmphasized,
        ]}
      >
        {label}
      </Text>

      <Animated.View
        style={[styles.indicator, { opacity: focus, transform: [{ scaleX: focus }] }]}
      />
    </Pressable>
  );
}

export function BottomNavigation({ state, navigation }: BottomTabBarProps) {
  const { t } = useTranslation();
  const insets = useSafeAreaInsets();

  return (
    <View style={[styles.bar, { paddingBottom: Math.max(insets.bottom, spacing.md) }]}>
      {state.routes.map((route, index) => {
        const meta = TAB_META[route.name as keyof MainTabParamList];
        const isFocused = state.index === index;

        const onPress = () => {
          const event = navigation.emit({
            type: 'tabPress',
            target: route.key,
            canPreventDefault: true,
          });

          if (!isFocused && !event.defaultPrevented) {
            navigation.navigate(route.name, route.params);
          }
        };

        return (
          <TabButton
            key={route.key}
            meta={meta}
            label={t(meta.labelKey)}
            isFocused={isFocused}
            onPress={onPress}
          />
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: colors.surface,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    paddingTop: spacing.sm,
    paddingHorizontal: spacing.sm,
  },
  tab: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'flex-start',
    gap: spacing.xs,
  },
  /** Fixed slot keeps every tab label on the same baseline. */
  iconSlot: {
    width: 44,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emphasizedIcon: {
    borderRadius: radii.pill,
    backgroundColor: colors.primaryMuted,
    ...shadows.raised,
  },
  emphasizedIconActive: {
    backgroundColor: colors.primary,
  },
  label: {
    ...typography.caption,
    fontSize: 11,
    color: colors.textMuted,
  },
  labelActive: {
    color: colors.primary,
  },
  labelEmphasized: {
    color: colors.primary,
    fontWeight: '700',
  },
  indicator: {
    width: 18,
    height: 2,
    borderRadius: radii.pill,
    backgroundColor: colors.primary,
    marginTop: 2,
  },
});
