import { currentUser } from '../../../lib/auth.js';
import { csrfValid } from '../../../lib/csrf.js';
import { getAcp } from '../../../lib/acp-service.js';
import { errorCode, isUuid, taskIdOf } from '../../../lib/acp-view.js';

// Staff only. The browser sends a form; THIS server signs the token and calls the ACP.
export const POST = async ({ request, cookies, redirect }) => {
  let me;
  try { me = await currentUser(cookies); } catch { return new Response('Database unavailable', { status: 503 }); }
  if (!me) return new Response('Not logged in', { status: 401 });
  if (!me.is_admin) return new Response('Forbidden: staff only', { status: 403 });

  const f = await request.formData();
  if (!csrfValid(cookies.get('session')?.value, String(f.get('csrf') || '')))
    return new Response('Forbidden: bad CSRF token', { status: 403 });

  // Same key = same task, so a double-click or a re-sent form never creates two.
  const key = String(f.get('idempotency_key') || '');
  if (!isUuid(key)) return redirect('/admin/diagnostics?error=bad_request', 303);

  const { acp } = getAcp();
  if (!acp) return redirect('/admin/diagnostics?error=not_configured', 303);

  try {
    const data = await acp.requestDiagnostic(me.acp_uuid, key.toLowerCase());
    const id = taskIdOf(data);
    return redirect(id ? `/admin/diagnostics/${id}` : '/admin/diagnostics', 303);
  } catch (e) {
    console.error('ACP request failed:', e.name, e.status ?? ''); // never log tokens or keys
    return redirect(`/admin/diagnostics?error=${errorCode(e)}`, 303);
  }
};
