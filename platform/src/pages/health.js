import { dbUp } from '../lib/db.js';
export const GET = async () =>
  new Response(JSON.stringify({ status: 'ok', db: (await dbUp()) ? 'up' : 'down' }), {
    headers: { 'content-type': 'application/json' },
  });
