import bcrypt from 'bcryptjs';
import { query } from '../../lib/db.js';
import { currentUser } from '../../lib/auth.js';

export const POST = async ({ request, cookies, redirect }) => {
  const me = await currentUser(cookies);
  if (!me || !me.is_admin) return new Response('forbidden', { status: 403 });
  const f = await request.formData();
  const username = String(f.get('username') || '').trim();
  const display = String(f.get('display_name') || '').trim() || username;
  const password = String(f.get('password') || '');
  if (!/^[a-z0-9_.-]{3,32}$/.test(username) || password.length < 8)
    return redirect('/?msg=invalid', 303);
  await query(
    'insert into users (username, display_name, password_hash) values ($1, $2, $3) on conflict (username) do nothing',
    [username, display, await bcrypt.hash(password, 10)]);
  return redirect('/?msg=created', 303);
};
