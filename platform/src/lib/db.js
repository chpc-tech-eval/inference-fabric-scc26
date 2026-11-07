import pg from 'pg';
import bcrypt from 'bcryptjs';
import { randomUUID } from 'node:crypto';

const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL, max: 5 });
let ready = null;

export function init() {
  if (!ready) {
    ready = (async () => {
      await pool.query(`create table if not exists users (
        id serial primary key,
        username text unique not null,
        display_name text not null,
        password_hash text not null,
        is_admin boolean not null default false,
        created_at timestamptz not null default now())`);
      // Week 4: stable per-user UUID, used as the ACP token subject (never the username or row id).
      // Generated in Node so it works on any Postgres version; existing users are backfilled.
      await pool.query('alter table users add column if not exists acp_uuid uuid');
      const missing = await pool.query('select id from users where acp_uuid is null');
      for (const row of missing.rows)
        await pool.query('update users set acp_uuid = $1 where id = $2 and acp_uuid is null', [randomUUID(), row.id]);
      await pool.query('create unique index if not exists users_acp_uuid_key on users (acp_uuid)');
      const adminPw = process.env.ADMIN_PASSWORD;
      if (adminPw) {
        const h = await bcrypt.hash(adminPw, 10);
        await pool.query(
          `insert into users (username, display_name, password_hash, is_admin, acp_uuid)
           values ('admin', 'Administrator', $1, true, $2) on conflict (username) do nothing`, [h, randomUUID()]);
      }
    })().catch((e) => { ready = null; throw e; });
  }
  return ready;
}

export const query = (...args) => pool.query(...args);

export async function dbUp() {
  try { await pool.query('select 1'); return true; } catch { return false; }
}
