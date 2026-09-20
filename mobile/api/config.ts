/**
 * Centralised API configuration. Every base-URL / endpoint / timeout constant
 * the app uses lives here — nothing else in the codebase hard-codes a URL.
 *
 * Resolution order:
 *  1. `EXPO_PUBLIC_API_URL` from `mobile/.env` (Expo inlines `EXPO_PUBLIC_*`
 *     at bundle time). The member expression `process.env.EXPO_PUBLIC_API_URL`
 *     must be written out in full — do NOT destructure `process.env`.
 *  2. The Expo / Metro bundler host — the same PC Expo Go already reached —
 *     on port 8000. A physical phone's `localhost` / `127.0.0.1` is the phone
 *     itself, so those names are never used as the API host.
 *  3. Android *emulator* only: `10.0.2.2` (the development machine).
 *  4. `localhost` for iOS Simulator / web.
 *
 * See `mobile/.env.example` to pin a backend explicitly.
 */

/** Loopback names that must never be used as the API host on a physical device. */
function isLoopbackHost(host: string): boolean {
  const normalised = host.toLowerCase().replace(/^\[/, '').replace(/\]$/, '');
  return (
    normalised === 'localhost' ||
    normalised === '127.0.0.1' ||
    normalised === '0.0.0.0' ||
    normalised === '::1' ||
    normalised === '::'
  );
}

/** Hosts that only the Android emulator (or Genymotion) can use to reach the PC. */
function isEmulatorOnlyHost(host: string): boolean {
  return host === '10.0.2.2' || host === '10.0.3.2';
}

/** Tunnel hostnames Expo uses for the JS bundle — they are not the FastAPI host. */
function isBundlerTunnelHost(host: string): boolean {
  const normalised = host.toLowerCase();
  return (
    normalised.endsWith('.exp.direct') ||
    normalised.endsWith('.expo.dev') ||
    normalised.endsWith('.ngrok.io') ||
    normalised.endsWith('.ngrok-free.app')
  );
}

function isUnusableApiHost(host: string): boolean {
  return isLoopbackHost(host) || isBundlerTunnelHost(host);
}

/**
 * Pull a hostname out of a URI (`http://192.168.1.10:8081/index.bundle?...`)
 * or a host:port string (`192.168.1.10:8081`). Loopback / tunnel hosts are
 * treated as missing so we never point the API at the phone or at Expo's
 * tunnel.
 */
function hostFromHint(value: string | undefined): string | undefined {
  if (!value) {
    return undefined;
  }

  const trimmed = value.trim();
  if (!trimmed) {
    return undefined;
  }

  const withScheme = /^[a-z][a-z0-9+.-]*:\/\//i.test(trimmed) ? trimmed : `http://${trimmed}`;
  try {
    const url = new URL(withScheme);
    if (!url.hostname || isUnusableApiHost(url.hostname)) {
      return undefined;
    }
    return url.hostname;
  } catch {
    const host = trimmed.split('/')[0]?.split(':')[0];
    if (host && !isUnusableApiHost(host)) {
      return host;
    }
    return undefined;
  }
}

function readOptionalString(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim().length > 0 ? value.trim() : undefined;
}

/**
 * Hostname of the machine serving Metro / Expo Go. On a physical device this is
 * the development PC's LAN address; it is not a hard-coded IP.
 *
 * Native modules are required inside try/catch so Jest (Node) can import this
 * file without a React Native runtime.
 */
function developmentMachineHost(): string | undefined {
  const hints: Array<string | undefined> = [];

  try {
    // Expo Go / dev client report the bundler as host:port (no hard-coded IP).
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const Constants = require('expo-constants').default as {
      expoConfig?: { hostUri?: string; extra?: { apiUrl?: unknown } };
      expoGoConfig?: { debuggerHost?: string };
      linkingUri?: string;
    };
    hints.push(readOptionalString(Constants?.expoConfig?.hostUri));
    hints.push(readOptionalString(Constants?.expoGoConfig?.debuggerHost));
    hints.push(readOptionalString(Constants?.linkingUri));
    hints.push(readOptionalString(Constants?.expoConfig?.extra?.apiUrl));
  } catch {
    // Jest / Node, or expo-constants unavailable.
  }

  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { NativeModules } = require('react-native') as {
      NativeModules?: { SourceCode?: { scriptURL?: string } };
    };
    hints.push(readOptionalString(NativeModules?.SourceCode?.scriptURL));
  } catch {
    // Jest / Node, or SourceCode unavailable on newer RN / Expo 54.
  }

  for (const hint of hints) {
    const host = hostFromHint(hint);
    if (host) {
      return host;
    }
  }

  return undefined;
}

function isAndroidEmulator(): boolean {
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { Platform } = require('react-native') as {
      Platform: {
        OS: string;
        constants?: { Brand?: string; Model?: string; Fingerprint?: string; Product?: string };
      };
    };
    if (Platform.OS !== 'android') {
      return false;
    }
    const constants = Platform.constants ?? {};
    const blob = [constants.Fingerprint, constants.Model, constants.Brand, constants.Product]
      .join(' ')
      .toLowerCase();
    return /generic|emulator|vbox|sdk_gphone|android sdk/.test(blob);
  } catch {
    return false;
  }
}

function formatOriginHost(host: string): string {
  if (host.startsWith('[')) {
    return host;
  }
  return host.includes(':') ? `[${host}]` : host;
}

function fallbackApiUrl(): string {
  const host = developmentMachineHost();
  if (host && !(isEmulatorOnlyHost(host) && !isAndroidEmulator())) {
    return `http://${formatOriginHost(host)}:8000`;
  }

  // Android emulator: the development machine is reachable at 10.0.2.2, not localhost.
  if (isAndroidEmulator()) {
    return 'http://10.0.2.2:8000';
  }

  return 'http://localhost:8000';
}

/**
 * Keep this exact member expression so Expo can inline it. Empty string is treated
 * as unset so a blank `.env` entry does not produce an invalid URL.
 */
const CONFIGURED_API_URL = process.env.EXPO_PUBLIC_API_URL;

function apiUrlFromEnv(): string | undefined {
  const raw = typeof CONFIGURED_API_URL === 'string' ? CONFIGURED_API_URL.trim() : '';
  if (!raw) {
    return undefined;
  }

  try {
    const host = new URL(raw).hostname;
    // localhost / 127.0.0.1 on a physical phone is the phone, not the PC.
    // 10.0.2.2 on a physical phone is also unreachable (emulator-only).
    if (isUnusableApiHost(host) || (isEmulatorOnlyHost(host) && !isAndroidEmulator())) {
      return undefined;
    }
    return raw;
  } catch {
    return undefined;
  }
}

const RAW_API_URL = apiUrlFromEnv() ?? fallbackApiUrl();

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

/** True when the app is using the Metro-host / emulator fallback rather than `.env`. */
export const IS_DEFAULT_API_URL = apiUrlFromEnv() === undefined;
