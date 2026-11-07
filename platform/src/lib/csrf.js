// CSRF protection for state-changing forms (astro.config has checkOrigin: false, so we do our own).
// The token is an HMAC of the session cookie: it only works for that session, needs no storage,
// and a different site cannot read or guess it. Put it in a hidden form field; check it on POST.
import crypto from 'node:crypto';

const secret = () => process.env.SESSION_SECRET || '';
const mac = (session) => crypto.createHmac('sha256', secret()).update('csrf:' + session).digest('base64url');

export function csrfToken(session) {
  if (!session || !secret()) return null;
  return mac(session);
}

export function csrfValid(session, token) {
  if (!session || !secret() || typeof token !== 'string' || !token) return false;
  const a = Buffer.from(token), b = Buffer.from(mac(session));
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}
