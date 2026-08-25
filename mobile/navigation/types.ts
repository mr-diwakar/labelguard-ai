import { BottomTabScreenProps } from '@react-navigation/bottom-tabs';
import { CompositeScreenProps, NavigatorScreenParams } from '@react-navigation/native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';

import { DemoScanKey } from '../data/demoScans';
import type { CapturedImage } from '../api/client';
import { EvidenceItem } from '../types/inspection';

export type MainTabParamList = {
  Home: undefined;
  Scan: undefined;
  History: undefined;
  Profile: undefined;
};

export type RootStackParamList = {
  MainTabs: NavigatorScreenParams<MainTabParamList>;
  /**
   * Runs one real scan, then replaces itself with Result. Exactly one input is
   * used: `image` (a photo just captured by the camera, uploaded for backend OCR)
   * or `demoKey` (a bundled sample OCR reading). `image` wins if both are given.
   */
  Processing: { demoKey?: DemoScanKey; image?: CapturedImage };
  /** Consumer-first result overview shown after processing. */
  Result: { inspectionId: string };
  /** "What was verified?" — label-to-product check detail. */
  Verification: { inspectionId: string };
  /** Evidence artefacts list and capture experience. */
  Evidence: { inspectionId: string };
  /** Single evidence artefact. The item travels in the param so locally-added
   *  evidence (not present in the mock arrays) renders without a lookup. */
  EvidenceDetail: { item: EvidenceItem };
  Language: undefined;
  ComingSoon: { title: string; description: string };
};

/** Tab screens can also reach the screens stacked above the tab navigator. */
export type TabScreenProps<T extends keyof MainTabParamList> = CompositeScreenProps<
  BottomTabScreenProps<MainTabParamList, T>,
  NativeStackScreenProps<RootStackParamList>
>;

export type ProcessingScreenProps = NativeStackScreenProps<RootStackParamList, 'Processing'>;
export type ResultScreenProps = NativeStackScreenProps<RootStackParamList, 'Result'>;
export type VerificationScreenProps = NativeStackScreenProps<RootStackParamList, 'Verification'>;
export type EvidenceScreenProps = NativeStackScreenProps<RootStackParamList, 'Evidence'>;
export type EvidenceDetailScreenProps = NativeStackScreenProps<RootStackParamList, 'EvidenceDetail'>;
export type LanguageScreenProps = NativeStackScreenProps<RootStackParamList, 'Language'>;
export type ComingSoonScreenProps = NativeStackScreenProps<RootStackParamList, 'ComingSoon'>;

declare global {
  namespace ReactNavigation {
    interface RootParamList extends RootStackParamList {}
  }
}
