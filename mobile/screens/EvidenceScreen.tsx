import { Ionicons } from '@expo/vector-icons';
import { useRef, useState } from 'react';
import {
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useTranslation } from 'react-i18next';

import { AppHeader } from '../components/AppHeader';
import { EmptyState } from '../components/EmptyState';
import { EvidenceItemCard } from '../components/EvidenceItemCard';
import { FadeIn } from '../components/FadeIn';
import { PrimaryButton } from '../components/PrimaryButton';
import { ScreenContainer } from '../components/ScreenContainer';
import { SectionHeader } from '../components/SectionHeader';
import { getInspection } from '../data/inspectionStore';
import { EvidenceScreenProps } from '../navigation/types';
import { colors, radii, spacing, touchTarget, typography } from '../theme';
import { EvidenceItem, EvidenceType } from '../types/inspection';

type ComposerKind = 'MEASUREMENT' | 'NOTE';

interface CaptureAction {
  key: string;
  labelKey: string;
  icon: keyof typeof Ionicons.glyphMap;
  onPress: () => void;
}

export function EvidenceScreen({ navigation, route }: EvidenceScreenProps) {
  const { t } = useTranslation();
  const inspection = getInspection(route.params.inspectionId);

  // Seeded from the mock record; capture actions append to this local list so
  // the workflow is exercised end to end without a backend.
  const [items, setItems] = useState<EvidenceItem[]>(inspection?.evidence ?? []);
  const [composer, setComposer] = useState<ComposerKind | null>(null);
  const [expectedInput, setExpectedInput] = useState('');
  const [observedInput, setObservedInput] = useState('');
  const [noteInput, setNoteInput] = useState('');
  const idCounter = useRef(0);

  if (!inspection) {
    return (
      <ScreenContainer>
        <AppHeader
          title={t('evidence.title')}
          onBackPress={() => navigation.goBack()}
          backLabel={t('common.back')}
        />
        <EmptyState icon="document-outline" title={t('result.notFound')} />
      </ScreenContainer>
    );
  }

  const makeId = () => `local-${Date.now()}-${(idCounter.current += 1)}`;

  const prepend = (item: EvidenceItem) => setItems((previous) => [item, ...previous]);

  const addPlaceholderImage = (type: EvidenceType, noteKey: string) =>
    prepend({
      id: makeId(),
      type,
      note: t(noteKey),
      capturedAt: new Date().toISOString(),
      isPlaceholder: true,
    });

  const closeComposer = () => {
    setComposer(null);
    setExpectedInput('');
    setObservedInput('');
    setNoteInput('');
  };

  const saveMeasurement = () => {
    const expected = expectedInput.trim();
    const observed = observedInput.trim();
    const note = noteInput.trim();

    if (!expected && !observed && !note) {
      closeComposer();
      return;
    }

    prepend({
      id: makeId(),
      type: 'MEASUREMENT',
      expectedValue: expected || undefined,
      observedValue: observed || undefined,
      note: note || undefined,
      capturedAt: new Date().toISOString(),
    });
    closeComposer();
  };

  const saveNote = () => {
    const note = noteInput.trim();

    if (!note) {
      closeComposer();
      return;
    }

    prepend({ id: makeId(), type: 'NOTE', note, capturedAt: new Date().toISOString() });
    closeComposer();
  };

  const actions: CaptureAction[] = [
    {
      key: 'takePhoto',
      labelKey: 'evidence.takePhoto',
      icon: 'camera-outline',
      onPress: () => addPlaceholderImage('PRODUCT_IMAGE', 'evidence.newPhotoNote'),
    },
    {
      key: 'uploadImage',
      labelKey: 'evidence.uploadImage',
      icon: 'cloud-upload-outline',
      onPress: () => addPlaceholderImage('LABEL_IMAGE', 'evidence.newUploadNote'),
    },
    {
      key: 'addMeasurement',
      labelKey: 'evidence.addMeasurement',
      icon: 'speedometer-outline',
      onPress: () => setComposer('MEASUREMENT'),
    },
    {
      key: 'addNote',
      labelKey: 'evidence.addNote',
      icon: 'create-outline',
      onPress: () => setComposer('NOTE'),
    },
  ];

  return (
    <ScreenContainer>
      <AppHeader
        title={inspection.productName}
        subtitle={t('evidence.listSubtitle')}
        onBackPress={() => navigation.goBack()}
        backLabel={t('common.back')}
      />

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent}>
        <FadeIn>
          <SectionHeader title={t('evidence.captureTitle')} />
          <View style={styles.actionGrid}>
            {actions.map((action) => (
              <Pressable
                key={action.key}
                accessibilityRole="button"
                accessibilityLabel={t(action.labelKey)}
                onPress={action.onPress}
                style={({ pressed }) => [styles.actionButton, pressed && styles.actionButtonPressed]}
              >
                <Ionicons name={action.icon} size={22} color={colors.primary} />
                <Text style={styles.actionLabel}>{t(action.labelKey)}</Text>
              </Pressable>
            ))}
          </View>
        </FadeIn>

        <FadeIn delay={60} style={styles.section}>
          <SectionHeader title={t('evidence.itemsTitle')} />
          {items.length === 0 ? (
            <EmptyState
              icon="images-outline"
              title={t('evidence.emptyTitle')}
              description={t('evidence.emptyDescription')}
            />
          ) : (
            <View style={styles.list}>
              {items.map((item) => (
                <EvidenceItemCard
                  key={item.id}
                  item={item}
                  onPress={() => navigation.navigate('EvidenceDetail', { item })}
                />
              ))}
            </View>
          )}
        </FadeIn>

        <View style={styles.advisory}>
          <Ionicons name="shield-checkmark-outline" size={16} color={colors.textMuted} />
          <Text style={styles.advisoryText}>{t('evidence.advisory')}</Text>
        </View>
      </ScrollView>

      <Modal
        visible={composer !== null}
        transparent
        animationType="slide"
        onRequestClose={closeComposer}
      >
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
          style={styles.modalBackdrop}
        >
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>
              {composer === 'MEASUREMENT'
                ? t('evidence.measurementModalTitle')
                : t('evidence.noteModalTitle')}
            </Text>

            {composer === 'MEASUREMENT' && (
              <>
                <TextInput
                  value={expectedInput}
                  onChangeText={setExpectedInput}
                  placeholder={t('evidence.expectedPlaceholder')}
                  placeholderTextColor={colors.textMuted}
                  style={styles.input}
                  accessibilityLabel={t('evidence.measurementExpected')}
                />
                <TextInput
                  value={observedInput}
                  onChangeText={setObservedInput}
                  placeholder={t('evidence.observedPlaceholder')}
                  placeholderTextColor={colors.textMuted}
                  style={styles.input}
                  accessibilityLabel={t('evidence.measurementObserved')}
                />
              </>
            )}

            <TextInput
              value={noteInput}
              onChangeText={setNoteInput}
              placeholder={t('evidence.notePlaceholder')}
              placeholderTextColor={colors.textMuted}
              style={[styles.input, styles.inputMultiline]}
              multiline
              accessibilityLabel={t('evidence.noteLabel')}
            />

            <View style={styles.modalActions}>
              <PrimaryButton
                label={t('evidence.cancel')}
                variant="outline"
                onPress={closeComposer}
                fullWidth
                style={styles.modalButton}
              />
              <PrimaryButton
                label={t('evidence.save')}
                icon="checkmark-outline"
                onPress={composer === 'MEASUREMENT' ? saveMeasurement : saveNote}
                fullWidth
                style={styles.modalButton}
              />
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  scrollContent: {
    paddingBottom: spacing.xxxl,
  },
  section: {
    marginTop: spacing.xl,
  },
  actionGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
  },
  actionButton: {
    flexGrow: 1,
    flexBasis: '46%',
    minHeight: touchTarget + 24,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.md,
    borderRadius: radii.md,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.primaryBorder,
  },
  actionButtonPressed: {
    backgroundColor: colors.surfaceMuted,
  },
  actionLabel: {
    ...typography.cardTitle,
    color: colors.primary,
    flexShrink: 1,
  },
  list: {
    gap: spacing.md,
  },
  advisory: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginTop: spacing.xl,
    paddingHorizontal: spacing.xs,
  },
  advisoryText: {
    flex: 1,
    ...typography.caption,
    fontWeight: '400',
    color: colors.textMuted,
  },
  modalBackdrop: {
    flex: 1,
    justifyContent: 'flex-end',
    backgroundColor: colors.overlay,
  },
  modalCard: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: radii.xl,
    borderTopRightRadius: radii.xl,
    padding: spacing.xl,
    gap: spacing.md,
  },
  modalTitle: {
    ...typography.sectionTitle,
    color: colors.textPrimary,
  },
  input: {
    ...typography.body,
    color: colors.textPrimary,
    minHeight: touchTarget,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceMuted,
  },
  inputMultiline: {
    minHeight: touchTarget + 24,
    textAlignVertical: 'top',
  },
  modalActions: {
    flexDirection: 'row',
    gap: spacing.md,
    marginTop: spacing.sm,
  },
  modalButton: {
    flex: 1,
  },
});
