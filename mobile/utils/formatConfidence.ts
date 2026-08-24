/**
 * Formats a 0..1 confidence score as a whole-number percentage. Returns an
 * em dash when the score is absent so the UI never implies false precision.
 */
export function formatConfidence(confidence?: number): string {
  return confidence === undefined ? '—' : `${Math.round(confidence * 100)}%`;
}
