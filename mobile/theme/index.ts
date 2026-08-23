import { Platform, TextStyle } from 'react-native';

export const colors = {
  primary: '#0F2A47',
  primaryDeep: '#0A1D33',
  primaryMuted: '#1B3B5F',
  primarySoft: '#E8EEF5',
  primaryBorder: '#C9D8E6',

  success: '#0E7C66',
  successSoft: '#E3F3EF',
  successBorder: '#B7DED4',

  warning: '#B4690E',
  warningSoft: '#FDF1E0',
  warningBorder: '#F0D5AC',

  danger: '#B42318',
  dangerSoft: '#FCEDEB',
  dangerBorder: '#F2C9C4',

  /** Reserved for Manual Review, kept distinct from the navy brand colour. */
  info: '#1660A8',
  infoSoft: '#E6F0FA',
  infoBorder: '#BAD4EC',

  background: '#F6F8FA',
  surface: '#FFFFFF',
  surfaceMuted: '#F1F4F8',

  textPrimary: '#12253B',
  textSecondary: '#4A5C70',
  textMuted: '#78889B',
  textInverse: '#FFFFFF',
  textInverseMuted: '#B9CBDD',

  border: '#E2E8F0',
  divider: '#EDF1F6',
  overlay: 'rgba(15, 42, 71, 0.55)',
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  xxxl: 32,
} as const;

export const radii = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  pill: 999,
} as const;

/**
 * Minimum height/width for anything tappable, per accessibility guidance.
 */
export const touchTarget = 48;

/** Durations in ms. Kept short so the UI never feels like it is waiting on itself. */
export const motion = {
  fast: 150,
  base: 220,
  slow: 300,
  counter: 700,
  breathe: 2600,
} as const;

export const typography = {
  heroTitle: {
    fontSize: 24,
    lineHeight: 30,
    fontWeight: '700',
    letterSpacing: -0.3,
  },
  greeting: {
    fontSize: 13,
    lineHeight: 18,
    fontWeight: '500',
  },
  screenTitle: {
    fontSize: 26,
    lineHeight: 32,
    fontWeight: '700',
    letterSpacing: -0.3,
  },
  sectionTitle: {
    fontSize: 17,
    lineHeight: 22,
    fontWeight: '700',
    letterSpacing: -0.1,
  },
  cardTitle: {
    fontSize: 15,
    lineHeight: 20,
    fontWeight: '600',
  },
  body: {
    fontSize: 14,
    lineHeight: 20,
    fontWeight: '400',
  },
  caption: {
    fontSize: 12,
    lineHeight: 16,
    fontWeight: '500',
  },
  stat: {
    fontSize: 24,
    lineHeight: 28,
    fontWeight: '700',
    letterSpacing: -0.5,
  },
  label: {
    fontSize: 11,
    lineHeight: 14,
    fontWeight: '700',
    letterSpacing: 0.6,
  },
} satisfies Record<string, TextStyle>;

export const shadows = {
  card: Platform.select({
    android: { elevation: 1 },
    web: { boxShadow: '0 2px 8px rgba(15, 42, 71, 0.06)' },
    default: {
      shadowColor: colors.primary,
      shadowOpacity: 0.06,
      shadowRadius: 8,
      shadowOffset: { width: 0, height: 2 },
    },
  }),
  raised: Platform.select({
    android: { elevation: 6 },
    web: { boxShadow: '0 6px 14px rgba(15, 42, 71, 0.18)' },
    default: {
      shadowColor: colors.primary,
      shadowOpacity: 0.18,
      shadowRadius: 14,
      shadowOffset: { width: 0, height: 6 },
    },
  }),
} as const;

export const theme = { colors, spacing, radii, typography, shadows, motion, touchTarget };
