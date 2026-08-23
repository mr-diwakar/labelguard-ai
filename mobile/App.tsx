import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { restoreSavedLanguage } from './i18n';
import { AppNavigator } from './navigation/AppNavigator';

export default function App() {
  const [languageReady, setLanguageReady] = useState(false);

  useEffect(() => {
    restoreSavedLanguage().finally(() => setLanguageReady(true));
  }, []);

  if (!languageReady) {
    return null;
  }

  return (
    <SafeAreaProvider>
      <StatusBar style="dark" />
      <AppNavigator />
    </SafeAreaProvider>
  );
}
