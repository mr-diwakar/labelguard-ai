import { Ionicons } from '@expo/vector-icons';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { useRef, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { AppHeader } from '../components/AppHeader';
import { PrimaryButton } from '../components/PrimaryButton';
import { ScreenContainer } from '../components/ScreenContainer';
import { Surface } from '../components/Surface';
import { DEFAULT_DEMO_KEY, DEMO_SCAN_ORDER, DemoScanKey, demoScans } from '../data/demoScans';
import { TabScreenProps } from '../navigation/types';
import { colors, radii, spacing, typography } from '../theme';

const CHECKLIST_KEYS = [
  'scan.clearlyVisible',
  'scan.wellLit',
  'scan.notBlurry',
  'scan.insideFrame',
];

export function ScanScreen({ navigation }: TabScreenProps<'Scan'>) {
  const { t } = useTranslation();

  const [permission, requestPermission] = useCameraPermissions();
  const cameraRef = useRef<CameraView | null>(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [capturing, setCapturing] = useState(false);
  const [captureErrorKey, setCaptureErrorKey] = useState<string | null>(null);

  // Secondary path, kept for devices/emulators without a usable camera: a bundled
  // sample OCR reading. The scan itself is real either way — only the source of
  // the OCR input differs.
  const [selectedKey, setSelectedKey] = useState<DemoScanKey>(DEFAULT_DEMO_KEY);

  const cameraGranted = permission?.granted === true;

  /**
   * Capture the label photo and hand it to `ProcessingScreen`, which uploads it
   * for backend OCR. A failed capture shows a message; it never crashes and never
   * navigates on with nothing, because a scan with no photo would have no input.
   */
  const handleCapture = async () => {
    const camera = cameraRef.current;
    if (!camera || capturing) {
      return;
    }
    setCapturing(true);
    setCaptureErrorKey(null);
    try {
      const photo = await camera.takePictureAsync({ quality: 0.7 });
      if (!photo?.uri) {
        setCaptureErrorKey('scan.captureFailed');
        return;
      }
      navigation.navigate('Processing', { image: { uri: photo.uri, format: photo.format } });
    } catch {
      setCaptureErrorKey('scan.captureFailed');
    } finally {
      setCapturing(false);
    }
  };

  const renderPreview = () => {
    if (cameraGranted) {
      return (
        <CameraView
          ref={cameraRef}
          style={styles.camera}
          facing="back"
          onCameraReady={() => setCameraReady(true)}
        />
      );
    }

    // permission === null means the check is still in flight (first render).
    if (!permission) {
      return (
        <View style={styles.previewFallback}>
          <ActivityIndicator color={colors.textInverse} />
          <Text style={styles.previewHint}>{t('scan.permissionChecking')}</Text>
        </View>
      );
    }

    const canAskAgain = permission.canAskAgain !== false;
    return (
      <View style={styles.previewFallback}>
        <Ionicons name="camera-outline" size={38} color={colors.textInverseMuted} />
        <Text style={styles.previewTitle}>{t('scan.permissionTitle')}</Text>
        <Text style={styles.previewHint}>
          {t(canAskAgain ? 'scan.permissionHint' : 'scan.permissionDeniedHint')}
        </Text>
        {canAskAgain && (
          <PrimaryButton
            label={t('scan.permissionGrant')}
            icon="lock-open-outline"
            onPress={() => {
              void requestPermission();
            }}
            style={styles.permissionButton}
          />
        )}
      </View>
    );
  };

  return (
    <ScreenContainer>
      <AppHeader title={t('scan.title')} subtitle={t('scan.subtitle')} />

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent}>
        <View style={styles.preview} accessibilityLabel={t('scan.title')}>
          {renderPreview()}

          <View style={[styles.corner, styles.cornerTopLeft]} />
          <View style={[styles.corner, styles.cornerTopRight]} />
          <View style={[styles.corner, styles.cornerBottomLeft]} />
          <View style={[styles.corner, styles.cornerBottomRight]} />
        </View>

        <Surface style={styles.checklistCard}>
          <Text style={styles.checklistTitle}>{t('scan.checklistTitle')}</Text>
          {CHECKLIST_KEYS.map((key) => (
            <View key={key} style={styles.checklistRow}>
              <Text style={styles.checklistGlyph}>✓</Text>
              <Text style={styles.checklistText}>{t(key)}</Text>
            </View>
          ))}
        </Surface>

        {cameraGranted && (
          <>
            <PrimaryButton
              label={capturing ? t('scan.capturing') : t('scan.capturePhoto')}
              icon="camera-outline"
              onPress={() => {
                void handleCapture();
              }}
              disabled={!cameraReady || capturing}
              fullWidth
              style={styles.captureButton}
            />
            {captureErrorKey && <Text style={styles.captureError}>{t(captureErrorKey)}</Text>}
          </>
        )}

        <Surface style={styles.sampleCard}>
          <Text style={styles.sampleTitle}>{t('scan.chooseSampleTitle')}</Text>
          <Text style={styles.sampleHint}>{t('scan.chooseSampleHint')}</Text>
          <View style={styles.sampleOptions}>
            {DEMO_SCAN_ORDER.map((key) => {
              const isActive = key === selectedKey;
              return (
                <Pressable
                  key={key}
                  accessibilityRole="button"
                  accessibilityState={{ selected: isActive }}
                  onPress={() => setSelectedKey(key)}
                  style={[styles.sampleChip, isActive && styles.sampleChipActive]}
                >
                  <Text style={[styles.sampleChipText, isActive && styles.sampleChipTextActive]}>
                    {t(demoScans[key].labelKey)}
                  </Text>
                </Pressable>
              );
            })}
          </View>
          <PrimaryButton
            label={t('scan.capture')}
            icon="scan-outline"
            variant="outline"
            onPress={() => navigation.navigate('Processing', { demoKey: selectedKey })}
            fullWidth
            style={styles.sampleButton}
          />
        </Surface>

        <Text style={styles.footnote}>{t('scan.footnote')}</Text>
      </ScrollView>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  scrollContent: {
    paddingBottom: spacing.xxxl,
  },
  preview: {
    width: '100%',
    aspectRatio: 3 / 4,
    maxHeight: 420,
    borderRadius: radii.xl,
    backgroundColor: colors.primaryDeep,
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  camera: {
    ...StyleSheet.absoluteFillObject,
  },
  previewFallback: {
    ...StyleSheet.absoluteFillObject,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
    padding: spacing.xxl,
  },
  corner: {
    position: 'absolute',
    width: 34,
    height: 34,
    borderColor: colors.textInverseMuted,
  },
  cornerTopLeft: {
    top: spacing.xl,
    left: spacing.xl,
    borderTopWidth: 2,
    borderLeftWidth: 2,
    borderTopLeftRadius: radii.sm,
  },
  cornerTopRight: {
    top: spacing.xl,
    right: spacing.xl,
    borderTopWidth: 2,
    borderRightWidth: 2,
    borderTopRightRadius: radii.sm,
  },
  cornerBottomLeft: {
    bottom: spacing.xl,
    left: spacing.xl,
    borderBottomWidth: 2,
    borderLeftWidth: 2,
    borderBottomLeftRadius: radii.sm,
  },
  cornerBottomRight: {
    bottom: spacing.xl,
    right: spacing.xl,
    borderBottomWidth: 2,
    borderRightWidth: 2,
    borderBottomRightRadius: radii.sm,
  },
  previewTitle: {
    ...typography.cardTitle,
    color: colors.textInverse,
    marginTop: spacing.sm,
  },
  previewHint: {
    ...typography.caption,
    fontWeight: '400',
    color: colors.textInverseMuted,
    textAlign: 'center',
  },
  permissionButton: {
    marginTop: spacing.md,
  },
  checklistCard: {
    marginTop: spacing.xl,
    gap: spacing.sm,
  },
  checklistTitle: {
    ...typography.cardTitle,
    color: colors.textPrimary,
    marginBottom: spacing.xs,
  },
  checklistRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  checklistGlyph: {
    fontSize: 13,
    lineHeight: 18,
    fontWeight: '700',
    color: colors.success,
  },
  checklistText: {
    ...typography.body,
    color: colors.textSecondary,
  },
  sampleCard: {
    marginTop: spacing.xl,
    gap: spacing.sm,
  },
  sampleTitle: {
    ...typography.cardTitle,
    color: colors.textPrimary,
  },
  sampleHint: {
    ...typography.caption,
    fontWeight: '400',
    color: colors.textSecondary,
  },
  sampleOptions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    marginTop: spacing.xs,
  },
  sampleChip: {
    minHeight: 40,
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderRadius: radii.pill,
    borderWidth: 1,
    borderColor: colors.primaryBorder,
    backgroundColor: colors.surface,
  },
  sampleChipActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  sampleChipText: {
    ...typography.caption,
    color: colors.primaryMuted,
  },
  sampleChipTextActive: {
    color: colors.textInverse,
  },
  captureButton: {
    marginTop: spacing.xl,
  },
  captureError: {
    ...typography.caption,
    fontWeight: '400',
    color: colors.warning,
    textAlign: 'center',
    marginTop: spacing.sm,
  },
  sampleButton: {
    marginTop: spacing.md,
  },
  footnote: {
    ...typography.caption,
    fontWeight: '400',
    color: colors.textMuted,
    textAlign: 'center',
    marginTop: spacing.md,
  },
});
