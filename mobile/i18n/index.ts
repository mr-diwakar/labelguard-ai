import AsyncStorage from '@react-native-async-storage/async-storage';
import { getLocales } from 'expo-localization';
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import bn from './locales/bn.json';
import en from './locales/en.json';
import gu from './locales/gu.json';
import hi from './locales/hi.json';
import mr from './locales/mr.json';
import ta from './locales/ta.json';
import te from './locales/te.json';

export interface SupportedLanguage {
  code: string;
  /** Shown in the picker, in the language's own script. */
  nativeName: string;
  englishName: string;
}

export const SUPPORTED_LANGUAGES: SupportedLanguage[] = [
  { code: 'en', nativeName: 'English', englishName: 'English' },
  { code: 'hi', nativeName: 'हिन्दी', englishName: 'Hindi' },
  { code: 'mr', nativeName: 'मराठी', englishName: 'Marathi' },
  { code: 'bn', nativeName: 'বাংলা', englishName: 'Bengali' },
  { code: 'ta', nativeName: 'தமிழ்', englishName: 'Tamil' },
  { code: 'gu', nativeName: 'ગુજરાતી', englishName: 'Gujarati' },
  { code: 'te', nativeName: 'తెలుగు', englishName: 'Telugu' },
];

const resources = {
  en: { translation: en },
  hi: { translation: hi },
  mr: { translation: mr },
  bn: { translation: bn },
  ta: { translation: ta },
  gu: { translation: gu },
  te: { translation: te },
};

const FALLBACK_LANGUAGE = 'en';
const STORAGE_KEY = 'labelguard.language';

function isSupported(code: string): boolean {
  return SUPPORTED_LANGUAGES.some((language) => language.code === code);
}

/** Reads the device language, ignoring any region suffix such as "hi-IN". */
function detectDeviceLanguage(): string {
  const deviceCode = getLocales()[0]?.languageCode;

  return deviceCode && isSupported(deviceCode) ? deviceCode : FALLBACK_LANGUAGE;
}

i18n.use(initReactI18next).init({
  resources,
  lng: detectDeviceLanguage(),
  fallbackLng: FALLBACK_LANGUAGE,
  interpolation: { escapeValue: false },
});

/**
 * Applies a saved preference if one exists. Called once at startup, after
 * i18next has already initialised with the device language so the first
 * render is never blank.
 */
export async function restoreSavedLanguage(): Promise<void> {
  try {
    const saved = await AsyncStorage.getItem(STORAGE_KEY);

    if (saved && isSupported(saved) && saved !== i18n.language) {
      await i18n.changeLanguage(saved);
    }
  } catch {
    // A missing preference is not an error; the device language stays active.
  }
}

export async function setAppLanguage(code: string): Promise<void> {
  if (!isSupported(code)) {
    return;
  }

  await i18n.changeLanguage(code);

  try {
    await AsyncStorage.setItem(STORAGE_KEY, code);
  } catch {
    // The language still changes for this session even if saving fails.
  }
}

export default i18n;
