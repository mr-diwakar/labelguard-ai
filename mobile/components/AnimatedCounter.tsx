import { useEffect, useRef, useState } from 'react';
import { Animated, StyleProp, Text, TextStyle } from 'react-native';

import { motion } from '../theme';

interface AnimatedCounterProps {
  value: number;
  style?: StyleProp<TextStyle>;
  duration?: number;
}

/**
 * Counts up to the target value once on mount. The driver stays on the JS
 * thread because the displayed text has to be rebuilt on every frame.
 */
export function AnimatedCounter({ value, style, duration = motion.counter }: AnimatedCounterProps) {
  const progress = useRef(new Animated.Value(0)).current;
  const [displayed, setDisplayed] = useState(0);

  useEffect(() => {
    const listenerId = progress.addListener(({ value: fraction }) => {
      setDisplayed(Math.round(fraction * value));
    });

    progress.setValue(0);
    Animated.timing(progress, { toValue: 1, duration, useNativeDriver: false }).start();

    return () => progress.removeListener(listenerId);
  }, [duration, progress, value]);

  return <Text style={style}>{displayed}</Text>;
}
