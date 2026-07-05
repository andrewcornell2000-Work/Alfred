# lean-ctx — Optional Context Compression

lean-ctx complements native Cursor tools and Alfred domain MCPs. It is **not** a replacement for Read/Grep/Shell on normal repo work.

Full skill: `skills/lean-ctx.md` · Cursor rule: `cursor/rules/lean-ctx.mdc` (optional, `alwaysApply: false`)

## Default
- **Read / Grep / Glob / Shell / Edit / Write** → native Cursor tools
- **Excel / Power BI / GitHub / browser** → domain MCPs per `skills/mcp-routing.md`

## When lean-ctx helps
| Situation | Tool |
|-----------|------|
| Large file (>500 lines) overview | `ctx_read(path, "map")` |
| Targeted region | `ctx_read(path, "lines:N-M")` |
| Re-read after edit | `ctx_read(path, "diff")` |
| Big repo search | `ctx_search(pattern, path)` |
| Noisy shell output | `lean-ctx -c "git log --oneline -20"` |
| Cross-session facts | `ctx_knowledge` remember / recall |

## Bail-out rule
If lean-ctx MCP errors or exceeds ~5 seconds, **do not retry** — use native tools for the rest of the turn.

Do **not** call `ctx_overview` or `ctx_compose` on every turn or at session start unless the task is genuinely unfamiliar and large.

## Setup
Installed by `Alfred-Install.exe` / `setup.ps1` → `lean-ctx onboard` merges into Cursor/Claude/Codex configs.
Re-run `Provision-Cursor.ps1` after updates to keep cooperative rules (optional lean-ctx, native default).

Verify: `lean-ctx doctor` · Savings: `lean-ctx gain`
