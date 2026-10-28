import pg from 'pg';
import bcrypt from 'bcryptjs';

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
      const adminPw = process.env.ADMIN_PASSWORD;
      if (adminPw) {
        const h = await bcrypt.hash(adminPw, 10);
        await pool.query(
          `insert into users (username, display_name, password_hash, is_admin)
           values ('admin', 'Administrator', $1, true) on conflict (username) do nothing`, [h]);
      }
    })().catch((e) => { ready = null; throw e; });
  }
  return ready;
}

export const query = (...args) => pool.query(...args);

export async function dbUp() {
  try { await pool.query('select 1'); return true; } catch { return false; }
}
