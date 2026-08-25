/**
 * Unit tests for the one HTTP client (`postScan`). Every failure mode must
 * collapse to a typed `ScanApiError` with the right `kind`; the UI switches on
 * that. `fetch` is mocked so nothing here touches the network.
 */

import { postScan, ScanApiError } from '../api/client';
import { SCAN_ENDPOINT } from '../api/config';
import type { ScanRequest, ScanResult } from '../api/types';

const REQUEST: ScanRequest = { scan_id: 'test' };

const OK_RESULT: ScanResult = {
  scan_id: 'test',
  declarations: [],
  verification: [],
  ingredients: [],
  evidence: [],
  stages: [],
  warnings: [],
};

function jsonResponse(body: unknown, init: { ok?: boolean; status?: number } = {}) {
  return {
    ok: init.ok ?? true,
    status: init.status ?? 200,
    json: async () => body,
  };
}

const originalFetch = (global as { fetch?: unknown }).fetch;

afterEach(() => {
  (global as { fetch?: unknown }).fetch = originalFetch;
  jest.useRealTimers();
});

describe('postScan — success', () => {
  it('POSTs JSON to the scan endpoint and returns the parsed result', async () => {
    const fetchMock = jest.fn(async () => jsonResponse(OK_RESULT));
    (global as { fetch?: unknown }).fetch = fetchMock;

    const result = await postScan(REQUEST);

    expect(result).toEqual(OK_RESULT);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(SCAN_ENDPOINT);
    expect(init.method).toBe('POST');
    expect(init.body).toBe(JSON.stringify(REQUEST));
    expect((init.headers as Record<string, string>)['Content-Type']).toBe('application/json');
  });
});

describe('postScan — error mapping', () => {
  it('maps a non-2xx status to kind "http" with the status and parsed detail', async () => {
    (global as { fetch?: unknown }).fetch = jest.fn(async () =>
      jsonResponse({ detail: 'bad input' }, { ok: false, status: 422 }),
    );
    const err = await postScan(REQUEST).catch((e) => e);
    expect(err).toBeInstanceOf(ScanApiError);
    expect(err.kind).toBe('http');
    expect(err.status).toBe(422);
    expect(err.detail).toBe('bad input');
  });

  it('parses a structured { error: { message } } envelope for the detail', async () => {
    (global as { fetch?: unknown }).fetch = jest.fn(async () =>
      jsonResponse({ error: { code: 'X', message: 'engine down' } }, { ok: false, status: 500 }),
    );
    const err = await postScan(REQUEST).catch((e) => e);
    expect(err.kind).toBe('http');
    expect(err.detail).toBe('engine down');
  });

  it('maps a fetch TypeError (unreachable server) to kind "network"', async () => {
    (global as { fetch?: unknown }).fetch = jest.fn(async () => {
      throw new TypeError('Failed to fetch');
    });
    const err = await postScan(REQUEST).catch((e) => e);
    expect(err).toBeInstanceOf(ScanApiError);
    expect(err.kind).toBe('network');
  });

  it('maps an unreadable 2xx body to kind "malformed"', async () => {
    (global as { fetch?: unknown }).fetch = jest.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => {
        throw new SyntaxError('Unexpected token');
      },
    }));
    const err = await postScan(REQUEST).catch((e) => e);
    expect(err.kind).toBe('malformed');
  });

  it('maps our own timeout abort to kind "timeout"', async () => {
    jest.useFakeTimers();
    // A fetch that only settles when its signal aborts.
    (global as { fetch?: unknown }).fetch = jest.fn(
      (_url: string, init: RequestInit) =>
        new Promise((_resolve, reject) => {
          init.signal?.addEventListener('abort', () => {
            const e = new Error('aborted');
            e.name = 'AbortError';
            reject(e);
          });
        }),
    );

    const promise = postScan(REQUEST, { timeoutMs: 100 });
    const assertion = expect(promise).rejects.toMatchObject({ kind: 'timeout' });
    jest.advanceTimersByTime(100);
    await assertion;
  });

  it('maps a caller-cancelled request (external abort) to kind "network"', async () => {
    (global as { fetch?: unknown }).fetch = jest.fn(
      (_url: string, init: RequestInit) =>
        new Promise((_resolve, reject) => {
          const onAbort = () => {
            const e = new Error('aborted');
            e.name = 'AbortError';
            reject(e);
          };
          if (init.signal?.aborted) onAbort();
          else init.signal?.addEventListener('abort', onAbort);
        }),
    );

    const controller = new AbortController();
    controller.abort(); // already aborted before the call
    const err = await postScan(REQUEST, { signal: controller.signal }).catch((e) => e);
    expect(err).toBeInstanceOf(ScanApiError);
    expect(err.kind).toBe('network');
  });
});
