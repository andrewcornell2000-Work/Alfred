# MCP Tools

Documents MCP (Model Context Protocol) server tools used or evaluated for Alfred.
Alfred uses Claude Code's built-in MCP runtime; MCP servers are configured per-session
via `claude mcp add` rather than being hard-installed globally.

## Currently Configured

None — no persistent MCP servers installed at setup time.

---

## Learning Mode: Adding MCP Tools

When Alfred encounters or learns about a new MCP server during a session:

1. **Add an entry** in the [Candidate Tools](#candidate-tools) section below with:
   - Install command (npm package, pip package, or Docker image)
   - Purpose and which Alfred routing category it serves
   - Trust level: `official` | `community` | `experimental`
   - Whether it has destructive capabilities (`destructive: true/false`)

2. **Update `alfred-tools.json`** — add the tool to the `mcp.tools` array.

3. **Update install manifests** if a persistent install step is needed:
   - npm package → add to `requirements/npm-tools.txt` and `alfred-tools.json`
   - pip package → add to `requirements/python-requirements.txt` and `alfred-tools.json`

4. **Update `setup.ps1`** only if a new install step is needed that the manifest loop
   does not already handle automatically.

5. **Update `README.md`** if the tool changes the user-facing setup flow (e.g. new
   login step, new API key).

6. **Commit all manifest changes before the session ends.**

### Hard Rules

- Never store MCP server credentials, tokens, or API keys in this file or any manifest.
- Tools marked `destructive: true` must be represented in Alfred's safety gate in
  `backend/main.py` (`DANGEROUS_KEYWORDS` and dispatch checks) before they are
  allowed to dispatch.
- Never auto-pull from GitHub or auto-install tools without explicit user approval.
  The update flow in `check-updates.ps1` always prompts first.

---

## Candidate Tools

*(None yet — add entries here as Alfred encounters new MCP servers.)*

<!--
Example entry format:

### mcp-server-filesystem
- **Install:** `npm install -g @modelcontextprotocol/server-filesystem`
- **Command:** `mcp-server-filesystem`
- **Purpose:** Gives Claude Code scoped read/write access to local directories
- **Trust:** official
- **Destructive:** true (can write/delete files - represent in `DANGEROUS_KEYWORDS` and dispatch checks)
- **Notes:** Requires explicit directory allow-list at runtime via --allowed-dir flag
-->
