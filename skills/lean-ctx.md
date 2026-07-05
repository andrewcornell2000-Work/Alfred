# LeanCTX — Context Compression Layer

Alfred 2.0 ships with **LeanCTX** alongside Alfred's domain MCPs. LeanCTX governs tokens
between your repo and the agent — it does not replace Power BI, Excel, or GitHub MCPs.

## When to use LeanCTX vs Alfred MCPs

| Task | Use |
|------|-----|
| Read/search code in repo | Native Read/Grep (Cursor default); LeanCTX `ctx_read` map mode for large files / re-reads |
| Compressed git/npm/shell output | `lean-ctx -c "git status"` or shell hooks (auto) |
| Session memory / agent diary | LeanCTX `ctx_knowledge`, `ctx_session` |
| Durable business facts (entities, conventions) | LeanCTX `ctx_knowledge` — memory MCP retired |
| Live Excel workbook (open) | Alfred `excel` MCP (excellm) |
| Excel closed file / Power Query | Alfred `excel-mcp` — never ping-pong with excellm |
| Power BI model | `powerbi-modeling-mcp` |
| Power BI report visuals | `pbi-cli` (not the modeling MCP) |
| GitHub PRs/issues | Alfred `github` MCP |
| Web research (live/news/latest) | Alfred Tavily (direct API) |
| Library docs (React, DAX libs, SDKs) | Alfred `context7` MCP |
| Finance OneDrive files (outside repo) | Alfred `filesystem` MCP — not for Alfred repo code (use LeanCTX there) |

## Key commands

```bash
lean-ctx read path/to/file -m map      # API surface, ~13 tokens on re-read
lean-ctx -c "git status"               # compressed shell output
lean-ctx gain                          # show token savings
lean-ctx doctor                        # verify wiring
lean-ctx doctor --fix                  # repair MCP + hooks after Cursor/Alfred updates
lean-ctx overview                      # project recap after a new chat
```

## Setup (fresh machine)

Installed automatically by `Alfred-Install.exe` / `setup.ps1`:

1. `npm install -g lean-ctx-bin`
2. Alfred provisions domain MCPs first (`Provision-Cursor.ps1`)
3. `lean-ctx onboard` merges LeanCTX into Cursor + Claude + Codex configs
4. As the **last** provision step, `Provision-Cursor.ps1` force-overwrites Alfred's cooperative `lean-ctx.mdc` into `~/.cursor/rules` (and the project repo). lean-ctx onboard alone installs an aggressive always-on rule that can hang Cursor — Alfred always wins on install/update.

**No API keys or accounts required** for core use.

## Cursor hang / silent failures

If agents stop responding or tool calls hang for minutes, lean-ctx was likely forced on every read. Alfred sets `lean-ctx.mdc` to **optional** (`alwaysApply: false`) and `00-agent-tooling.mdc` makes native tools the default. Re-run:

```powershell
.\Provision-Cursor.ps1 -SkipClaude -SkipCodex
```

Optional opt-ins during setup:
anonymous telemetry, auto-updates, external providers — all declined by default in Alfred's bootstrap path.

## After install

Restart Cursor, Claude Code, and Codex once. Then run `lean-ctx gain` after a coding session to see savings.

## Cursor shows lean-ctx error

Cursor does not support `autoApprove` in `~/.cursor/mcp.json` (lean-ctx onboard adds it). Fix:

```powershell
lean-ctx doctor --fix
.\Provision-Cursor.ps1 -SkipClaude -SkipCodex   # strips autoApprove + fixes hook paths
```

Then fully restart Cursor.

## Disable temporarily

```bash
lean-ctx-off    # current shell only
lean-ctx-on     # re-enable
```

Full removal: `lean-ctx uninstall` (does not remove Alfred MCPs).
