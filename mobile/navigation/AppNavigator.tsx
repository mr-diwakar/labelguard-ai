import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { DefaultTheme, NavigationContainer, Theme } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

import { BottomNavigation } from '../components/BottomNavigation';
import { ComingSoonScreen } from '../screens/ComingSoonScreen';
import { EvidenceScreen } from '../screens/EvidenceScreen';
import { HistoryScreen } from '../screens/HistoryScreen';
import { HomeScreen } from '../screens/HomeScreen';
import { LanguageScreen } from '../screens/LanguageScreen';
import { ProcessingScreen } from '../screens/ProcessingScreen';
import { ProfileScreen } from '../screens/ProfileScreen';
import { ScanScreen } from '../screens/ScanScreen';
import { colors } from '../theme';
import { MainTabParamList, RootStackParamList } from './types';

const Tabs = createBottomTabNavigator<MainTabParamList>();
const Stack = createNativeStackNavigator<RootStackParamList>();

const navigationTheme: Theme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    primary: colors.primary,
    background: colors.background,
    card: colors.surface,
    text: colors.textPrimary,
    border: colors.border,
  },
};

function MainTabs() {
  return (
    <Tabs.Navigator
      initialRouteName="Home"
      screenOptions={{ headerShown: false, animation: 'fade' }}
      tabBar={(props) => <BottomNavigation {...props} />}
    >
      <Tabs.Screen name="Home" component={HomeScreen} />
      <Tabs.Screen name="Scan" component={ScanScreen} />
      <Tabs.Screen name="History" component={HistoryScreen} />
      <Tabs.Screen name="Profile" component={ProfileScreen} />
    </Tabs.Navigator>
  );
}

export function AppNavigator() {
  return (
    <NavigationContainer theme={navigationTheme}>
      <Stack.Navigator screenOptions={{ headerShown: false, animation: 'slide_from_right' }}>
        <Stack.Screen name="MainTabs" component={MainTabs} />
        <Stack.Screen name="Processing" component={ProcessingScreen} />
        <Stack.Screen name="Evidence" component={EvidenceScreen} />
        <Stack.Screen name="Language" component={LanguageScreen} />
        <Stack.Screen name="ComingSoon" component={ComingSoonScreen} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
