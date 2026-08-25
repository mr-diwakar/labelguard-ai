/**
 * Centralised API configuration. Every base-URL / endpoint / timeout constant
 * the app uses lives here — nothing else in the codebase hard-codes a URL.
 *
 * Base URL comes from `EXPO_PUBLIC_API_URL`. Expo inlines `EXPO_PUBLIC_*` at
 * build time by *statically* replacing the exact member expression
 * `process.env.EXPO_PUBLIC_API_URL` in the source, so it must be written out in
 * full here — do NOT destructure `process.env` or read it through a variable, or
 * the value will be `undefined` at runtime. When unset (the common local-dev
 * case), we fall back to the Metro host's default backend origin.
 *
 * See `mobile/.env.example` for how to point the app at a real backend.
 */

const DEFAULT_API_URL = 'http://localhost:8000';

const RAW_API_URL = process.env.EXPO_PUBLIC_API_URL ?? DEFAULT_API_URL;

/** Backend origin with any trailing slash(es) trimmed (so path joins are clean). */
export const API_BASE_URL = RAW_API_URL.replace(/\/+$/, '');

/** Versioned API prefix — matches the backend's `app/api/router.py`. */
export const API_PREFIX = '/api/v1';

/** Full URL of the unified scan endpoint. */
export const SCAN_ENDPOINT = `${API_BASE_URL}${API_PREFIX}/scan`;

/**
 * Full URL of the image-capture front door. It runs the SAME backend pipeline as
 * `SCAN_ENDPOINT`; the only difference is where the OCR input comes from — the
 * backend reads it off the uploaded photo instead of receiving it as JSON.
 */
export const SCAN_IMAGE_ENDPOINT = `${SCAN_ENDPOINT}/image`;

/**
 * How long a scan may run before the client aborts it. The backend orchestrator
 * is synchronous and fast for the demo OCR payloads, but a cold DB connection on
 * the legal stage can add latency, so this is generous.
 */
export const SCAN_TIMEOUT_MS = 15000;

/**
 * Image scans get a longer budget: the upload itself takes time, and the backend
 * additionally decodes, preprocesses and OCRs the photo before the pipeline runs.
 */
export const SCAN_IMAGE_TIMEOUT_MS = 45000;

/** True when the app is talking to the built-in default rather than a configured backend. */
export const IS_DEFAULT_API_URL = RAW_API_URL === DEFAULT_API_URL;
