import {
  b64,
  encodeRecord,
} from './carrier.js';

function endpoint(base, path) {
  return `${base.replace(/\/$/, '')}${path}`;
}

function errorResult(state, reason, details = {}) {
  return {
    ok: false,
    state,
    error: reason,
    ...details,
  };
}

export function createSubmitClient({
  baseUrl,
  fetchImpl = globalThis.fetch?.bind(globalThis),
  identity,
} = {}) {
  if (typeof baseUrl !== 'string' || !baseUrl) {
    throw new TypeError('baseUrl required');
  }
  if (typeof fetchImpl !== 'function') {
    throw new TypeError('fetchImpl required');
  }
  if (!identity || !(identity.secretKey instanceof Uint8Array) || identity.secretKey.length !== 64) {
    throw new TypeError('identity.secretKey required');
  }

  const submit = async atom => {
    let encoded;
    try {
      encoded = await encodeRecord(atom, identity.secretKey);
    } catch (error) {
      return errorResult('invalid', error?.message || 'invalid record');
    }

    const payload = {
      records: [
        {
          address: encoded.address,
          sha256: encoded.sha256,
          record: b64(encoded.record),
        },
      ],
    };

    let response;
    try {
      response = await fetchImpl(endpoint(baseUrl, '/submit'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
    } catch (error) {
      return errorResult('network', 'node unreachable', { message: error?.message || 'network error' });
    }

    let body = null;
    try {
      body = await response.json();
    } catch {
      body = null;
    }

    if (response.status === 200) {
      const result = Array.isArray(body?.results) ? body.results[0] : null;
      return {
        ok: true,
        state: result?.state || 'VALID',
        mid: result?.address || encoded.address,
        address: result?.address || encoded.address,
        sha256: result?.sha256 || encoded.sha256,
        duplicate: Boolean(result?.duplicate),
        head: body?.head ?? null,
        seq: body?.seq ?? null,
      };
    }

    if (response.status === 400) {
      const reason = typeof body?.error === 'string' ? body.error : 'invalid record';
      return errorResult('invalid', reason, { message: reason });
    }

    return errorResult('unsupported', `unsupported response status ${response.status}`, {
      status: response.status,
      message: typeof body?.error === 'string' ? body.error : null,
    });
  };

  return { submit };
}
