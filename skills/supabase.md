# Supabase

Use Supabase MCP + agent skills for database, auth, edge functions, and migrations.

## Setup (Alfred provision)

1. Add to Alfred `.env` (copy from `.env.template`):

   ```text
   SUPABASE_PROJECT_REF=your-project-ref
   SUPABASE_DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.your-project-ref.supabase.co:5432/postgres
   ```

2. Re-run provision:

   ```powershell
   powershell -ExecutionPolicy Bypass -File Provision-Cursor.ps1
   ```

3. Agent skills (installed automatically by provision, or run manually):

   ```powershell
   npx skills add supabase/agent-skills
   ```

## MCP (Cursor)

- Server: `supabase` — remote MCP at `https://mcp.supabase.com/mcp?project_ref=...`
- OAuth in Cursor on first use
- Auto-skipped if `SUPABASE_PROJECT_REF` is missing from `.env`

## Workflow

- Before schema changes: `list_tables`
- Debugging: `get_logs`, `get_advisors` before edits
- Client config: `get_project_url`, `get_publishable_keys`
- Migrations: `apply_migration` (destructive — confirm intent first)

## Direct Postgres

Use `SUPABASE_DATABASE_URL` from `.env` for app code or CLI tools. Never commit passwords.

Docs: https://supabase.com/docs/guides/getting-started/ai-skills
