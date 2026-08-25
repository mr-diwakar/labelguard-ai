/**
 * The sync→async seam.
 *
 * Screens read inspection data **synchronously** (`getInspection(id)`), exactly as
 * they did with the mock accessor. The async host — `ProcessingScreen` — runs the
 * real scan, adapts the `ScanResult`, and `putInspection`s the result here before
 * navigating on. So a live scan and a bundled demo record are read through one
 * accessor, and every screen's props and the `{ inspectionId }` navigation
 * contract stay unchanged.
 *
 * This is a module-level cache, not persistence: like the mock data it augments,
 * it does not survive an app restart. Live scans are looked up by `scan_id`;
 * anything not found here falls back to the bundled demo records.
 */

import { findMockInspection } from './mockInspections';
import type { DemoScanKey } from './demoScans';
import type { Inspection } from '../types/inspection';

const liveInspections = new Map<string, Inspection>();
/** Remembers which demo produced a stored inspection, so "Verify Again" can re-run it. */
const demoKeyById = new Map<string, DemoScanKey>();

/** Store a freshly-scanned inspection, optionally recording the demo key that produced it. */
export function putInspection(inspection: Inspection, demoKey?: DemoScanKey): void {
  liveInspections.set(inspection.id, inspection);
  if (demoKey) {
    demoKeyById.set(inspection.id, demoKey);
  }
}

/**
 * Resolve an inspection by id: a live scan if one was stored, otherwise a bundled
 * demo record (tagged `source: 'DEMO'`). Returns undefined when neither exists,
 * matching the previous `findMockInspection` contract the screens already handle.
 */
export function getInspection(id: string): Inspection | undefined {
  const live = liveInspections.get(id);
  if (live) {
    return live;
  }
  const mock = findMockInspection(id);
  if (mock) {
    return { ...mock, source: mock.source ?? 'DEMO' };
  }
  return undefined;
}

/** The demo key a stored inspection came from, if it was a demo scan. */
export function getDemoKeyFor(id: string): DemoScanKey | undefined {
  return demoKeyById.get(id);
}

/** Clears the store. Test-only helper; not used by the app. */
export function resetInspectionStore(): void {
  liveInspections.clear();
  demoKeyById.clear();
}
