import { BottomTabScreenProps } from '@react-navigation/bottom-tabs';
import { CompositeScreenProps, NavigatorScreenParams } from '@react-navigation/native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';

export type MainTabParamList = {
  Home: undefined;
  Scan: undefined;
  History: undefined;
  Profile: undefined;
};

export type RootStackParamList = {
  MainTabs: NavigatorScreenParams<MainTabParamList>;
  Processing: { inspectionId: string };
  Evidence: { inspectionId: string };
  Language: undefined;
  ComingSoon: { title: string; description: string };
};

/** Tab screens can also reach the screens stacked above the tab navigator. */
export type TabScreenProps<T extends keyof MainTabParamList> = CompositeScreenProps<
  BottomTabScreenProps<MainTabParamList, T>,
  NativeStackScreenProps<RootStackParamList>
>;

export type ProcessingScreenProps = NativeStackScreenProps<RootStackParamList, 'Processing'>;
export type EvidenceScreenProps = NativeStackScreenProps<RootStackParamList, 'Evidence'>;
export type LanguageScreenProps = NativeStackScreenProps<RootStackParamList, 'Language'>;
export type ComingSoonScreenProps = NativeStackScreenProps<RootStackParamList, 'ComingSoon'>;

declare global {
  namespace ReactNavigation {
    interface RootParamList extends RootStackParamList {}
  }
}
