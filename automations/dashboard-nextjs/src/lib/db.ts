import { Pool } from 'pg';

const pool = new Pool({
  user: process.env.PG_USER || 'venu',
  host: process.env.PG_HOST || '127.0.0.1',
  database: process.env.PG_DATABASE || 'pinterest_db',
  password: process.env.PG_PASSWORD || 'venu',
  port: parseInt(process.env.PG_PORT || '5432'),
});

export const query = (text: string, params?: any[]) => pool.query(text, params);
