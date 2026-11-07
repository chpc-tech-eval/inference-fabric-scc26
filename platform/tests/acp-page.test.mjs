import test from 'node:test';
import assert from 'node:assert/strict';
import { csrfToken, csrfValid } from '../src/lib/csrf.js';
import { AcpError, AcpUnavailable } from '../src/lib/acp.js';
import { askerUuid, errorCode, explanationText, isUuid, messageForCode, normalizeDetail, normalizeList, outcome, taskIdOf } from '../src/lib/acp-view.js';

const U = '3f2b8c1e-5d4a-4e6f-9a7b-1c2d3e4f5a6b';

test('csrf: valid only for the same session', () => {
  process.env.SESSION_SECRET = 'test-secret';
  const t = csrfToken('session-A');
  assert.ok(csrfValid('session-A', t));
  assert.ok(!csrfValid('session-B', t));
  assert.ok(!csrfValid('session-A', t + 'x'));
  assert.ok(!csrfValid('session-A', ''));
  assert.ok(!csrfValid('', t));
  assert.ok(!csrfValid('session-A', undefined));
});

test('csrf: refuses everything when no secret is set', () => {
  process.env.SESSION_SECRET = 'test-secret';
  const t = csrfToken('s');
  delete process.env.SESSION_SECRET;
  assert.equal(csrfToken('s'), null);
  assert.ok(!csrfValid('s', t));
  process.env.SESSION_SECRET = 'test-secret';
});

test('failures are never shown as healthy', () => {
  assert.equal(outcome({ status: 'failed', error_code: 'diagnostic_no_data' }).label, 'No metrics found');
  assert.equal(outcome({ status: 'failed', error_code: 'worker_interrupted' }).label, 'Interrupted, please request again');
  assert.equal(outcome({ status: 'failed', error_code: 'model_unavailable' }).label, 'Explanation failed');
  assert.equal(outcome({ status: 'failed' }).tone, 'bad');
  assert.equal(outcome({ status: 'mystery' }).kind, 'unknown');
  assert.equal(outcome({ status: 'mystery' }).tone, 'bad');
  assert.equal(outcome({}).kind, 'unknown');
});

test('progress and success states', () => {
  assert.ok(outcome({ status: 'queued' }).inProgress);
  assert.ok(outcome({ status: 'running' }).inProgress);
  const ok = outcome({ status: 'succeeded' });
  assert.equal(ok.tone, 'ok');
  assert.ok(!ok.inProgress);
});

test('no-data wins even if status says succeeded', () => {
  assert.equal(outcome({ status: 'succeeded' }, { error_code: 'diagnostic_no_data' }).kind, 'no_data');
});

test('response shapes are read defensively', () => {
  assert.deepEqual(normalizeList({ tasks: [1, 2] }), [1, 2]);
  assert.deepEqual(normalizeList([3]), [3]);
  assert.deepEqual(normalizeList(null), []);
  assert.equal(taskIdOf({ id: U }), U);
  assert.equal(taskIdOf({ task: { task_id: U } }), U);
  assert.equal(taskIdOf({ id: '../x' }), null);
  const d = normalizeDetail({ task: { status: 'succeeded' }, run: { evidence: { v: 1 } }, explanation: 'hi', events: [{}] });
  assert.deepEqual(d.evidence, { v: 1 });
  assert.equal(explanationText(d.explanation), 'hi');
  assert.equal(d.events.length, 1);
  assert.deepEqual(normalizeDetail(null).events, []);
  assert.equal(explanationText(null), null);
});

test('asker is read from the token subject', () => {
  assert.equal(askerUuid({ subject: `urn:quantum-platform:user:${U.toUpperCase()}` }), U);
  assert.equal(askerUuid({}), null);
});

test('error codes and messages', () => {
  assert.equal(errorCode(new AcpUnavailable('x')), 'unreachable');
  assert.equal(errorCode(new AcpError(401, 'x')), 'http_401');
  assert.equal(errorCode(new Error('x')), 'internal');
  assert.match(messageForCode('http_401'), /clocks/);
  assert.equal(messageForCode('<script>'), null);
  assert.equal(messageForCode(null), null);
  assert.ok(isUuid(U) && !isUuid('abc'));
});
