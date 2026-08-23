import { ReactNode, useEffect, useRef } from 'react';
import { Animated, StyleProp, ViewStyle } from 'react-native';

import { motion } from '../theme';

interface FadeInProps {
  children: ReactNode;
  /** Staggers sections so the screen settles top-to-bottom. */
  delay?: number;
  /** How far the content rises as it appears, in pixels. */
  distance?: number;
  duration?: number;
  style?: StyleProp<ViewStyle>;
}

export function FadeIn({
  children,
  delay = 0,
  distance = 14,
  duration = motion.slow,
  style,
}: FadeInProps) {
  const progress = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(progress, {
      toValue: 1,
      duration,
      delay,
      useNativeDriver: true,
    }).start();
  }, [delay, duration, progress]);

  const translateY = progress.interpolate({ inputRange: [0, 1], outputRange: [distance, 0] });

  return (
    <Animated.View style={[{ opacity: progress, transform: [{ translateY }] }, style]}>
      {children}
    </Animated.View>
  );
}
