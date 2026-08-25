/**
 * The one HTTP client for the scan backend. Every network call the app makes
 * goes through `postScan` (structured OCR JSON) or `postScanImage` (a captured
 * photo); there is no raw `fetch` anywhere else. Both hit the same backend
 * pipeline and return the same `ScanResult`. All the ways a request can fail are
 * collapsed into a single typed `ScanApiError` whose `kind` the UI switches on to
 * pick a message — the caller never sees a raw `TypeError`, an `AbortError`, or
 * an unparsed HTTP body.
 */

import { SCAN_ENDPOINT, SCAN_IMAGE_ENDPOINT, SCAN_IMAGE_TIMEOUT_MS, SCAN_TIMEOUT_MS } from './config';
import type { ScanRequest, ScanResult } from './types';

/**
 * Why a scan call failed, in terms the UI can map to a message + a retry:
 *  - `network`  : request never reached the server (offline, wrong host, CORS,
 *                 connection refused). `fetch` rejects with a TypeError.
 *  - `timeout`  : the request was aborted after SCAN_TIMEOUT_MS.
 *  - `http`     : the server answered with a non-2xx status (`status` set).
 *  - `malformed`: a 2xx response whose body was not the JSON we expect.
 */
export type ScanApiErrorKind = 'network' | 'timeout' | 'http' | 'malformed';

export class ScanApiError extends Error {
  readonly kind: ScanApiErrorKind;
  /** HTTP status, present only when `kind === 'http'`. */
  readonly status?: number;
  /** Server-supplied detail string, when one could be parsed. */
  readonly detail?: string;

  constructor(kind: ScanApiErrorKind, message: string, opts: { status?: number; detail?: string } = {}) {
    super(message);
    this.name = 'ScanApiError';
    this.kind = kind;
    this.status = opts.status;
    this.detail = opts.detail;
  }
}

export interface PostScanOptions {
  /** Overrides the default per-request timeout. */
  timeoutMs?: number;
  /** An external abort signal (e.g. screen unmount); composed with the timeout. */
  signal?: AbortSignal;
}

/** Best-effort extraction of a human-readable detail from an error response body. */
function detailFromErrorBody(body: unknown): string | undefined {
  if (!body || typeof body !== 'object') {
    return undefined;
  }
  const record = body as Record<string, unknown>;
  // FastAPI validation errors and our own handler both use `detail`;
  // a structured `{ error: { code, message } }` envelope is also supported.
  const error = record.error;
  if (error && typeof error === 'object') {
    const message = (error as Record<string, unknown>).message;
    if (typeof message === 'string' && message.length > 0) {
      return message;
    }
  }
  const detail = record.detail;
  if (typeof detail === 'string' && detail.length > 0) {
    return detail;
  }
  return undefined;
}

/**
 * Shared transport for both scan entry points: send one request, map every
 * failure mode onto `ScanApiError`, and parse a `ScanResult` out of a 2xx body.
 * The two public functions differ only in URL, body encoding and timeout — the
 * error handling below is deliberately the single copy of that logic.
 */
async function sendScan(
  url: string,
  init: { headers: Record<string, string>; body: BodyInit },
  timeoutMs: number,
  options: PostScanOptions,
): Promise<ScanResult> {
  const controller = new AbortController();
  const timedOut = { value: false };
  const timeoutId = setTimeout(() => {
    timedOut.value = true;
    controller.abort();
  }, timeoutMs);

  // Forward an external abort (e.g. the screen unmounting) to our controller.
  const onExternalAbort = () => controller.abort();
  if (options.signal) {
    if (options.signal.aborted) {
      controller.abort();
    } else {
      options.signal.addEventListener('abort', onExternalAbort);
    }
  }

  let response: Response;
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: init.headers,
      body: init.body,
      signal: controller.signal,
    });
  } catch (cause) {
    // AbortController.abort() surfaces as an AbortError DOMException/Error.
    if (timedOut.value) {
      throw new ScanApiError('timeout', `Scan request timed out after ${timeoutMs}ms.`);
    }
    if (cause instanceof Error && cause.name === 'AbortError') {
      // Aborted by the caller's signal, not our timeout.
      throw new ScanApiError('network', 'Scan request was cancelled.');
    }
    throw new ScanApiError('network', 'Could not reach the scan service.');
  } finally {
    clearTimeout(timeoutId);
    if (options.signal) {
      options.signal.removeEventListener('abort', onExternalAbort);
    }
  }

  if (!response.ok) {
    let detail: string | undefined;
    try {
      detail = detailFromErrorBody(await response.json());
    } catch {
      detail = undefined;
    }
    throw new ScanApiError('http', `Scan service returned HTTP ${response.status}.`, {
      status: response.status,
      detail,
    });
  }

  try {
    return (await response.json()) as ScanResult;
  } catch {
    throw new ScanApiError('malformed', 'Scan service returned an unreadable response.');
  }
}

/**
 * POST one `ScanRequest` to `/api/v1/scan` and return the parsed `ScanResult`.
 * Rejects only with `ScanApiError`. Never throws synchronously.
 */
export async function postScan(request: ScanRequest, options: PostScanOptions = {}): Promise<ScanResult> {
  return sendScan(
    SCAN_ENDPOINT,
    {
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(request),
    },
    options.timeoutMs ?? SCAN_TIMEOUT_MS,
    options,
  );
}

/** What the camera captured, as `expo-camera` reports it. */
export interface CapturedImage {
  /** Local `file://` URI of the photo on the device. */
  uri: string;
  /** Container format, used only to name the upload part sensibly. */
  format?: string;
}

/** Content type for the upload part, inferred from the URI/format expo-camera gave us. */
function imageMimeType(image: CapturedImage): string {
  const hint = (image.format ?? image.uri.split('.').pop() ?? '').toLowerCase();
  if (hint === 'png') return 'image/png';
  if (hint === 'webp') return 'image/webp';
  return 'image/jpeg';
}

/**
 * Upload one captured label photo to `/api/v1/scan/image` and return the parsed
 * `ScanResult`. The backend — not the app — does the image validation and OCR,
 * then runs the exact same scan pipeline as `postScan`; this function only
 * transports the photo, so there is no second OCR or compliance path in the app.
 *
 * The `{ uri, name, type }` part is React Native's own FormData file form; the
 * `Content-Type` header is deliberately NOT set so the runtime can generate the
 * multipart boundary itself.
 */
export async function postScanImage(image: CapturedImage, options: PostScanOptions = {}): Promise<ScanResult> {
  const mimeType = imageMimeType(image);
  const extension = mimeType.split('/')[1];
  const form = new FormData();
  form.append('image', {
    uri: image.uri,
    name: `label.${extension}`,
    type: mimeType,
  } as unknown as Blob);

  return sendScan(
    SCAN_IMAGE_ENDPOINT,
    { headers: { Accept: 'application/json' }, body: form },
    options.timeoutMs ?? SCAN_IMAGE_TIMEOUT_MS,
    options,
  );
}
