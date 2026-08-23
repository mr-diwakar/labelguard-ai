import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';

import { SUPPORTED_LANGUAGES, setAppLanguage } from '../i18n';

/**
 * Wraps language state so screens do not talk to i18next directly.
 * Changing the language re-renders every subscribed component immediately.
 */
export function useAppLanguage() {
  const { i18n } = useTranslation();

  const currentCode = i18n.language;
  const current =
    SUPPORTED_LANGUAGES.find((language) => language.code === currentCode) ?? SUPPORTED_LANGUAGES[0];

  const changeLanguage = useCallback((code: string) => setAppLanguage(code), []);

  return { languages: SUPPORTED_LANGUAGES, current, currentCode, changeLanguage };
}
