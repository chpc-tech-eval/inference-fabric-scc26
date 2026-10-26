import bcrypt from 'bcryptjs';
import { init, query } from '../../lib/db.js';
import { makeToken, cookieOpts } from '../../lib/auth.js';

export const POST = async ({ request, cookies, redirect }) => {
  const f = await request.formData();
  const username = String(f.get('username') || '').trim();
  const password = String(f.get('password') || '');
  await init();
  const r = await query('select password_hash from users where username = $1', [username]);
  const ok = r.rows[0] && (await bcrypt.compare(password, r.rows[0].password_hash));
  if (!ok) return redirect('/?error=1', 303);
  cookies.set('session', makeToken(username), cookieOpts);
  return redirect('/', 303);
};
