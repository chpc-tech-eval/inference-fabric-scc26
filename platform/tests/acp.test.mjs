import test from 'node:test';
import assert from 'node:assert/strict';
import { generateKeyPairSync, verify, randomUUID } from 'node:crypto';
import { writeFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { AcpClient, AcpError, AcpUnavailable, configFromEnv, AUDIENCE } from '../src/lib/acp.js';

const USER = randomUUID();
const { publicKey, privateKey } = generateKeyPairSync('ed25519');
const keyPath = join(mkdtempSync(join(tmpdir(), 'acp-')), 'private.pem');
writeFileSync(keyPath, privateKey.export({ type: 'pkcs8', format: 'pem' }));

const cfg = { baseUrl: 'http://acp:8080', privateKeyPath: keyPath, issuer: 'test-issuer',
  subjectPrefix: 'urn:test:user:', tenantId: 'tenant-1', diagnostic: 'approved-diag', timeoutMs: 1000 };
const ok = (body = {}, status = 200) => ({ status, statusText: 'OK', json: async () => body });
function fake(res) {
  const calls = [];
  const f = async (url, init) => { calls.push({ url, init }); if (res instanceof Error) throw res; return res ?? ok(); };
  return { f, calls };
}
const dec = (s) => JSON.parse(Buffer.from(s, 'base64url').toString());

test('token claims and signature', () => {
  const t = new AcpClient(cfg, fake().f).signToken(USER);
  const [h, c, s] = t.split('.');
  assert.equal(dec(h).alg, 'EdDSA');
  assert.ok(verify(null, Buffer.from(`${h}.${c}`), publicKey, Buffer.from(s, 'base64url')));
  const claims = dec(c);
  assert.equal(claims.iss, 'test-issuer'); assert.equal(claims.aud, AUDIENCE);
  assert.equal(claims.sub, `urn:test:user:${USER}`);
  assert.equal(claims.tenant, 'tenant-1'); assert.equal(claims.scope, 'admin:diagnostics');
  assert.equal(claims.exp - claims.iat, 60); assert.equal(claims.nbf, claims.iat);
});

test('jti is fresh', () => {
  const cl = new AcpClient(cfg, fake().f);
  const ids = new Set(Array.from({ length: 5 }, () => dec(cl.signToken(USER).split('.')[1]).jti));
  assert.equal(ids.size, 5);
});

test('rejects non-UUID user', () => {
  assert.throws(() => new AcpClient(cfg, fake().f).signToken('alice'), /UUID/);
});

test('request shape and idempotency', async () => {
  const { f, calls } = fake(ok({ id: 'x' }, 201));
  const cl = new AcpClient(cfg, f);
  const key = randomUUID();
  await cl.requestDiagnostic(USER, key); await cl.requestDiagnostic(USER, key); await cl.requestDiagnostic(USER);
  assert.equal(calls[0].url, 'http://acp:8080/v1/admin/tasks');
  assert.equal(calls[0].init.method, 'POST');
  assert.equal(calls[0].init.body, '{"diagnostic":"approved-diag"}');
  assert.match(calls[0].init.headers.Authorization, /^Bearer /);
  assert.equal(calls[0].init.headers['Idempotency-Key'], key);
  assert.equal(calls[1].init.headers['Idempotency-Key'], key);
  assert.notEqual(calls[2].init.headers['Idempotency-Key'], key);
});

test('list and get', async () => {
  const { f, calls } = fake();
  const cl = new AcpClient(cfg, f);
  await cl.listTasks(USER, 50);
  const tid = randomUUID(); await cl.getTask(USER, tid);
  assert.equal(calls[0].url, 'http://acp:8080/v1/admin/tasks?offset=50');
  assert.equal(calls[1].url, `http://acp:8080/v1/admin/tasks/${tid}`);
});

test('blocks path injection and bad offsets', async () => {
  const cl = new AcpClient(cfg, fake().f);
  for (const bad of ['../secret', '1; drop', '', 'abc']) assert.throws(() => cl.getTask(USER, bad), /UUID/);
  for (const off of [-1, '5', 1.5, NaN]) assert.throws(() => cl.listTasks(USER, off), /offset/);
});

test('error mapping leaks nothing', async () => {
  const cl = new AcpClient(cfg, fake({ status: 401, statusText: 'Unauthorized' }).f);
  await assert.rejects(cl.listTasks(USER), (e) => e instanceof AcpError && e.status === 401 && !/Bearer/.test(e.message));
  const down = new AcpClient(cfg, fake(new Error('secret-host leak')).f);
  await assert.rejects(down.listTasks(USER), (e) => e instanceof AcpUnavailable && !/leak/.test(e.message));
});

test('non-JSON response', async () => {
  const cl = new AcpClient(cfg, fake({ status: 200, statusText: 'OK', json: async () => { throw new Error('x'); } }).f);
  await assert.rejects(cl.listTasks(USER), AcpError);
});

test('missing key file and missing env fail fast', () => {
  assert.throws(() => new AcpClient({ ...cfg, privateKeyPath: '/nope' }, fake().f));
  assert.throws(() => configFromEnv({}), /Missing required setting/);
});
