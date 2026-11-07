// Turns ACP responses into what the staff page shows. Pure functions, easy to test.
//
// ASSUMPTION TO VERIFY: the ACP's exact JSON field names are not in our guide (they are in
// agent-control-plane/docs/12-phase1.md). This file looks in the likely places. The detail page
// also shows the full raw response, so nothing is hidden if a name here is wrong. Fix names HERE only.
import { AcpError, AcpUnavailable } from './acp.js';

const UUID_RE = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
export const isUuid = (v) => typeof v === 'string' && new RegExp(`^${UUID_RE.source}$`, 'i').test(v);

export function normalizeList(data) {
  const arr = Array.isArray(data) ? data : (data?.tasks ?? data?.items ?? data?.results ?? []);
  return Array.isArray(arr) ? arr : [];
}

const taskOf = (data) => (data?.task && typeof data.task === 'object' ? data.task : data) ?? {};

export function taskIdOf(data) {
  const t = taskOf(data);
  const id = t.id ?? t.task_id ?? data?.task_id;
  return isUuid(id) ? id.toLowerCase() : null;
}

export function normalizeDetail(data) {
  const d = data && typeof data === 'object' ? data : {};
  const task = taskOf(d);
  const run = d.run ?? task.run ?? null;
  const events = d.events ?? task.events;
  return {
    task,
    run,
    evidence: d.evidence ?? run?.evidence ?? task.evidence ?? null,
    explanation: d.explanation ?? run?.explanation ?? task.explanation ?? null,
    events: Array.isArray(events) ? events : [],
  };
}

export function explanationText(x) {
  if (x == null || x === '') return null;
  if (typeof x === 'string') return x;
  return x.text ?? x.content ?? x.explanation ?? JSON.stringify(x, null, 2);
}

/** Who asked: the ACP stores the token subject, which ends in the user's UUID. */
export function askerUuid(task) {
  for (const k of ['created_by', 'requested_by', 'subject', 'sub', 'actor', 'user']) {
    const m = typeof task?.[k] === 'string' && task[k].match(UUID_RE);
    if (m) return m[0].toLowerCase();
  }
  return null;
}

export function createdAt(task) {
  return task?.created_at ?? task?.queued_at ?? task?.requested_at ?? null;
}

export function fmtTime(v) {
  const d = v ? new Date(v) : null;
  if (!d || Number.isNaN(d.getTime())) return v ? String(v) : '—';
  return d.toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
}

/**
 * What the status means for a person. Failures are never shown as healthy:
 *  - no data            -> "No metrics found"
 *  - model failure      -> "Explanation failed" (evidence is still shown by the page)
 *  - worker_interrupted -> "Interrupted, please request again"
 *  - anything unknown   -> shown as unknown, with the raw status
 */
export function outcome(task, run) {
  const parts = [task?.status, task?.error_code, task?.failure_code, task?.error?.code,
    typeof task?.error === 'string' ? task.error : null,
    run?.status, run?.error_code, run?.failure_code, run?.error?.code];
  const text = parts.filter((p) => typeof p === 'string').join(' ').toLowerCase();
  const status = String(task?.status ?? run?.status ?? 'unknown').toLowerCase();

  if (text.includes('no_data'))
    return { kind: 'no_data', tone: 'bad', label: 'No metrics found',
      detail: 'The diagnostic found no data. This is NOT a healthy result: nothing could be checked.' };
  if (text.includes('worker_interrupted'))
    return { kind: 'interrupted', tone: 'bad', label: 'Interrupted, please request again',
      detail: 'The worker stopped before finishing. Request the diagnostic again.' };
  if (/model|explanation/.test(text) && /fail|error|unavailable|timeout/.test(text))
    return { kind: 'explanation_failed', tone: 'bad', label: 'Explanation failed',
      detail: 'The model could not produce an explanation. The evidence below was collected before the model call.' };
  if (['queued', 'pending', 'accepted'].includes(status))
    return { kind: 'queued', tone: 'wait', inProgress: true, label: 'Queued', detail: 'Waiting for the worker.' };
  if (['running', 'in_progress', 'started'].includes(status))
    return { kind: 'running', tone: 'wait', inProgress: true, label: 'Running', detail: 'The worker is collecting evidence.' };
  if (['succeeded', 'success', 'completed', 'complete'].includes(status))
    return { kind: 'succeeded', tone: 'ok', label: 'Succeeded', detail: 'Check the evidence against Prometheus. The explanation is only an interpretation.' };
  if (/fail|error|cancel|timeout/.test(status))
    return { kind: 'failed', tone: 'bad', label: `Failed (${status})`, detail: 'The diagnostic did not complete.' };
  return { kind: 'unknown', tone: 'bad', label: `Unknown status: ${status}`, detail: 'Not recognised. Do not treat this as healthy. See the raw response.' };
}

/** Short code that is safe to put in a redirect URL. */
export function errorCode(e) {
  if (e instanceof AcpUnavailable) return 'unreachable';
  if (e instanceof AcpError) return `http_${e.status}`;
  return 'internal';
}

export function messageForCode(code) {
  if (typeof code !== 'string' || !/^(unreachable|not_configured|bad_request|internal|http_\d{3})$/.test(code)) return null;
  switch (code) {
    case 'unreachable': return 'The Agent Control Plane could not be reached. Check that it is running and that the network policy allows this website.';
    case 'not_configured': return 'The Agent Control Plane is not configured on this server (signing key or settings missing).';
    case 'bad_request': return 'Bad request. Reload the page and try again.';
    case 'internal': return 'Unexpected error. See the platform logs.';
    case 'http_401': return 'The ACP rejected our token (401). Check issuer, subject prefix, tenant, and that node clocks agree.';
    case 'http_403': return 'The ACP refused this request (403): scope or tenant not accepted.';
    case 'http_404': return 'The ACP did not find that (404).';
    case 'http_409':
    case 'http_422': return `The ACP rejected the request (${code.slice(5)}). Check the diagnostic name.`;
    default: return `The ACP returned an error (HTTP ${code.slice(5)}).`;
  }
}
