import { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { AppHeader } from '../components/AppHeader';
import { PrimaryButton } from '../components/PrimaryButton';
import { ScreenContainer } from '../components/ScreenContainer';
import { Surface } from '../components/Surface';
import { scanResultToInspection } from '../api/adapter';
import { postScan, postScanImage, ScanApiError } from '../api/client';
import type { ScanStageStatus } from '../api/types';
import { buildDemoRequest, DEFAULT_DEMO_KEY } from '../data/demoScans';
import { putInspection } from '../data/inspectionStore';
import { ProcessingScreenProps } from '../navigation/types';
import { colors, radii, spacing, typography } from '../theme';

type Phase = 'loading' | 'done' | 'error';

/** Backend stage id → i18n label. Unknown stages fall back to the raw id. */
const STAGE_LABEL_KEYS: Record<string, string> = {
  image: 'live.stageImage',
  ocr: 'live.stageOcr',
  extraction: 'live.stageExtraction',
  legal: 'live.stageLegal',
  verification: 'live.stageVerification',
  guidance: 'live.stageGuidance',
  nutrition: 'live.stageNutrition',
};

/** Shown as a neutral checklist while the request is in flight. */
const PIPELINE_STAGES = ['extraction', 'legal', 'verification', 'guidance', 'nutrition'];
const IMAGE_STAGES = ['image', 'ocr', ...PIPELINE_STAGES];

function stageLabel(stage: string, t: (key: string) => string): string {
  const key = STAGE_LABEL_KEYS[stage];
  return key ? t(key) : stage;
}

const STAGE_OUTCOME_PRESENTATION = {
  COMPLETED: { glyph: '✓', tint: colors.success, statusKey: 'live.stageCompleted' },
  SKIPPED: { glyph: '–', tint: colors.textMuted, statusKey: 'live.stageSkipped' },
  FAILED: { glyph: '⚠', tint: colors.warning, statusKey: 'live.stageFailed' },
} as const;

function errorMessageKey(error: ScanApiError): string {
  switch (error.kind) {
    case 'network':
      return 'live.errorNetwork';
    case 'timeout':
      return 'live.errorTimeout';
    case 'http':
      return 'live.errorHttp';
    case 'malformed':
      return 'live.errorMalformed';
    default:
      return 'live.errorNetwork';
  }
}

/**
 * Runs one real scan against the backend and shows its honest outcome.
 *
 * Two inputs, one pipeline: a photo just captured by the camera is uploaded to
 * `/scan/image`, where the backend reads the label text off it; a sample OCR
 * reading is POSTed to `/scan`. Everything after the OCR input — extraction,
 * legal, verification, guidance — is the same backend code either way, and this
 * screen never decides anything about the label itself.
 *
 * The backend is synchronous — it returns the whole `ScanResult` (with per-stage
 * `stages[]`) in a single response — so there is no real incremental progress to
 * animate. While the request is in flight we show a spinner and the pipeline
 * stages as a neutral checklist; when it resolves we show each stage's ACTUAL
 * outcome (completed / skipped / failed). Any failure is a typed `ScanApiError`
 * rendered as a retry card; the screen never crashes.
 */
export function ProcessingScreen({ navigation, route }: ProcessingScreenProps) {
  const { t } = useTranslation();
  const { demoKey, image } = route.params;
  const imageUri = image?.uri;
  const imageFormat = image?.format;

  const [phase, setPhase] = useState<Phase>('loading');
  const [stages, setStages] = useState<ScanStageStatus[]>([]);
  const [inspectionId, setInspectionId] = useState<string | null>(null);
  const [errorKey, setErrorKey] = useState<string>('live.errorNetwork');
  const [errorDetail, setErrorDetail] = useState<string | undefined>(undefined);
  const [attempt, setAttempt] = useState(0);

  // Keep the latest `t` without making the scan effect depend on locale changes.
  const tRef = useRef(t);
  tRef.current = t;

  useEffect(() => {
    let active = true;
    const controller = new AbortController();

    setPhase('loading');
    setStages([]);

    // A captured photo wins; otherwise fall back to the chosen sample reading.
    // `demoKey` is only used to re-run a demo scan, so its default is harmless.
    const scan = imageUri
      ? postScanImage({ uri: imageUri, format: imageFormat }, { signal: controller.signal })
      : postScan(buildDemoRequest(demoKey ?? DEFAULT_DEMO_KEY), { signal: controller.signal });

    scan
      .then((result) => {
        if (!active) return;
        const inspection = scanResultToInspection(result, {
          source: 'API',
          fallbackProductName: tRef.current('live.unnamedProduct'),
        });
        putInspection(inspection, imageUri ? undefined : demoKey);
        setStages(result.stages);
        setInspectionId(inspection.id);
        setPhase('done');
      })
      .catch((error) => {
        if (!active) return;
        if (error instanceof ScanApiError) {
          setErrorKey(errorMessageKey(error));
          setErrorDetail(error.detail);
        } else {
          setErrorKey('live.errorNetwork');
          setErrorDetail(undefined);
        }
        setPhase('error');
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [demoKey, imageUri, imageFormat, attempt]);

  return (
    <ScreenContainer>
      <AppHeader
        title={t('processing.title')}
        subtitle={t('processing.subtitle')}
        onBackPress={() => navigation.goBack()}
        backLabel={t('common.back')}
      />

      {phase === 'loading' && (
        <Surface style={styles.card}>
          <View style={styles.spinnerRow}>
            <ActivityIndicator color={colors.primary} />
            <Text style={styles.loadingTitle}>{t('processing.loadingTitle')}</Text>
          </View>
          <Text style={styles.loadingSubtitle}>
            {t(imageUri ? 'processing.loadingSubtitleImage' : 'processing.loadingSubtitle')}
          </Text>
          <View style={styles.stageList}>
            {(imageUri ? IMAGE_STAGES : PIPELINE_STAGES).map((stage) => (
              <View key={stage} style={styles.stageRow}>
                <Text style={[styles.stageGlyph, { color: colors.textMuted }]}>•</Text>
                <Text style={styles.stageLabel}>{stageLabel(stage, t)}</Text>
              </View>
            ))}
          </View>
        </Surface>
      )}

      {phase === 'done' && (
        <>
          <Surface style={styles.card}>
            <Text style={styles.completeTitle}>{t('processing.completeTitle')}</Text>
            <Text style={styles.completeDescription}>{t('processing.completeDescription')}</Text>
            <View style={styles.stageList}>
              {stages.map((stage) => {
                const presentation = STAGE_OUTCOME_PRESENTATION[stage.status];
                return (
                  <View key={stage.stage} style={styles.stageRow}>
                    <Text style={[styles.stageGlyph, { color: presentation.tint }]}>
                      {presentation.glyph}
                    </Text>
                    <Text style={styles.stageLabel}>{stageLabel(stage.stage, t)}</Text>
                    <Text style={styles.stageStatus}>{t(presentation.statusKey)}</Text>
                  </View>
                );
              })}
            </View>
          </Surface>
          <PrimaryButton
            label={t('processing.viewResult')}
            icon="document-text-outline"
            onPress={() => inspectionId && navigation.replace('Result', { inspectionId })}
            fullWidth
            style={styles.actionButton}
          />
        </>
      )}

      {phase === 'error' && (
        <Surface style={styles.card}>
          <Text style={styles.errorTitle}>{t('live.retryTitle')}</Text>
          <Text style={styles.errorMessage}>{t(errorKey)}</Text>
          {errorDetail && <Text style={styles.errorDetail}>{errorDetail}</Text>}
          <PrimaryButton
            label={t('live.retry')}
            icon="refresh-outline"
            onPress={() => setAttempt((count) => count + 1)}
            fullWidth
            style={styles.actionButton}
          />
        </Surface>
      )}
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  card: {
    marginTop: spacing.md,
  },
  spinnerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  loadingTitle: {
    ...typography.sectionTitle,
    color: colors.textPrimary,
  },
  loadingSubtitle: {
    ...typography.body,
    color: colors.textSecondary,
    marginTop: spacing.sm,
  },
  stageList: {
    marginTop: spacing.lg,
    gap: spacing.sm,
  },
  stageRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  stageGlyph: {
    fontSize: 14,
    lineHeight: 20,
    fontWeight: '700',
    width: 16,
    textAlign: 'center',
  },
  stageLabel: {
    ...typography.body,
    color: colors.textPrimary,
    flex: 1,
  },
  stageStatus: {
    ...typography.caption,
    fontWeight: '400',
    color: colors.textMuted,
  },
  completeTitle: {
    ...typography.sectionTitle,
    color: colors.textPrimary,
  },
  completeDescription: {
    ...typography.body,
    color: colors.textSecondary,
    marginTop: spacing.xs,
  },
  errorTitle: {
    ...typography.sectionTitle,
    color: colors.textPrimary,
  },
  errorMessage: {
    ...typography.body,
    color: colors.textSecondary,
    marginTop: spacing.sm,
  },
  errorDetail: {
    ...typography.caption,
    fontWeight: '400',
    color: colors.textMuted,
    marginTop: spacing.sm,
  },
  actionButton: {
    marginTop: spacing.lg,
  },
});
