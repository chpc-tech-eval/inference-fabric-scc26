// Server-side client for the Agent Control Plane (ACP). BACKEND ONLY.
// The private key and tokens must never reach the browser, logs or error messages.
// Contract: week4-role-frontend-project.md, Task 1. No dependencies (node:crypto signs Ed25519).
import { createPrivateKey, sign, randomUUID } from 'node:crypto';
import { readFileSync } from 'node:fs';

export const AUDIENCE = 'agent-control-plane';
export const SCOPE = 'admin:diagnostics';
export const TOKEN_TTL_SECONDS = 60; // ACP rejects anything over 90 s

export class AcpError extends Error {
  constructor(status, message) {
    super(`ACP returned HTTP ${status}: ${message}`);
    this.name = 'AcpError';
    this.status = status;
  }
}
export class AcpUnavailable extends Error {
  constructor(message) { super(message); this.name = 'AcpUnavailable'; }
}

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
function asUuid(value, what) {
  if (typeof value !== 'string' || !UUID_RE.test(value)) throw new Error(`${what} must be a UUID`);
  return value.toLowerCase();
}
const b64u = (b) => Buffer.from(b).toString('base64url');

/** Every setting is required: a missing one fails at startup, nothing is guessed. */
export function configFromEnv(env = process.env) {
  const need = (name) => {
    const v = (env[name] || '').trim();
    if (!v) throw new Error(`Missing required setting ${name}`);
    return v;
  };
  return {
    baseUrl: need('ACP_BASE_URL').replace(/\/+$/, ''),
    privateKeyPath: need('ACP_SIGNING_KEY_FILE'),
    issuer: need('ACP_JWT_ISSUER'),
    subjectPrefix: need('ACP_JWT_SUBJECT_PREFIX'),
    tenantId: need('ACP_TENANT_ID'),
    diagnostic: need('ACP_DIAGNOSTIC'),
    timeoutMs: 10000,
  };
}

export class AcpClient {
  #cfg; #key; #fetch;
  constructor(cfg, fetchImpl = globalThis.fetch) {
    this.#cfg = cfg;
    this.#fetch = fetchImpl;
    this.#key = createPrivateKey(readFileSync(cfg.privateKeyPath)); // fails fast if not mounted
  }

  /** Fresh 60-second token for one user (their stable UUID, not username or row id). */
  signToken(userUuid) {
    const now = Math.floor(Date.now() / 1000);
    const header = { alg: 'EdDSA', typ: 'JWT' };
    const claims = {
      iss: this.#cfg.issuer,
      aud: AUDIENCE,
      sub: `${this.#cfg.subjectPrefix}${asUuid(userUuid, 'userUuid')}`,
      tenant: this.#cfg.tenantId,
      scope: SCOPE,
      iat: now, nbf: now, exp: now + TOKEN_TTL_SECONDS,
      jti: randomUUID(),
    };
    const input = `${b64u(JSON.stringify(header))}.${b64u(JSON.stringify(claims))}`;
    return `${input}.${b64u(sign(null, Buffer.from(input), this.#key))}`;
  }

  /** Same Idempotency-Key returns the SAME task; omit for a genuinely new request. */
  requestDiagnostic(userUuid, idempotencyKey) {
    const key = idempotencyKey ? asUuid(idempotencyKey, 'idempotencyKey') : randomUUID();
    return this.#call('POST', '/v1/admin/tasks', userUuid, {
      body: { diagnostic: this.#cfg.diagnostic },
      headers: { 'Idempotency-Key': key },
    });
  }

  listTasks(userUuid, offset = 0) {
    if (!Number.isInteger(offset) || offset < 0) throw new Error('offset must be a non-negative integer');
    return this.#call('GET', `/v1/admin/tasks?offset=${offset}`, userUuid);
  }

  getTask(userUuid, taskId) {
    return this.#call('GET', `/v1/admin/tasks/${asUuid(taskId, 'taskId')}`, userUuid);
  }

  async #call(method, path, userUuid, { body, headers } = {}) {
    const h = { Authorization: `Bearer ${this.signToken(userUuid)}`, Accept: 'application/json', ...headers };
    if (body !== undefined) h['Content-Type'] = 'application/json';
    let res;
    try {
      res = await this.#fetch(this.#cfg.baseUrl + path, {
        method, headers: h,
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: AbortSignal.timeout(this.#cfg.timeoutMs),
      });
    } catch (e) {
      throw new AcpUnavailable(`ACP unreachable (${e?.name || 'error'})`); // type only, no details
    }
    if (res.status >= 400) throw new AcpError(res.status, res.statusText || 'error');
    try { return await res.json(); }
    catch { throw new AcpError(res.status, 'response was not valid JSON'); }
  }
}
