import crypto from 'node:crypto';
import { init, query } from './db.js';

const secret = () => process.env.SESSION_SECRET || '';
const sign = (v) => crypto.createHmac('sha256', secret()).update(v).digest('base64url');

export function makeToken(username) {
  const p = Buffer.from(JSON.stringify({ u: username, e: Date.now() + 8 * 3600 * 1000 })).toString('base64url');
  return p + '.' + sign(p);
}

export function readToken(token) {
  if (!token || !secret()) return null;
  const [p, s] = token.split('.');
  if (!p || !s) return null;
  const a = Buffer.from(s), b = Buffer.from(sign(p));
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return null;
  try {
    const d = JSON.parse(Buffer.from(p, 'base64url').toString());
    return d.e > Date.now() ? d.u : null;
  } catch { return null; }
}

export async function currentUser(cookies) {
  const u = readToken(cookies.get('session')?.value);
  if (!u) return null;
  await init();
  const r = await query('select username, display_name, is_admin from users where username = $1', [u]);
  return r.rows[0] || null;
}

export const cookieOpts = { httpOnly: true, secure: true, sameSite: 'lax', path: '/', maxAge: 8 * 3600 };
