# LeanCTX — Context Compression Layer

Alfred 2.0 ships with **LeanCTX** alongside Alfred's domain MCPs. LeanCTX governs tokens
between your repo and the agent — it does not replace Power BI, Excel, or GitHub MCPs.

## When to use LeanCTX vs Alfred MCPs

| Task | Use |
|------|-----|
| Read/search code in repo | `ctx_read` / `ctx_search` (LeanCTX) — map mode, cached re-reads |
| Compressed git/npm/shell output | `lean-ctx -c "git status"` or shell hooks (auto) |
| Session memory across chats | LeanCTX `ctx_*` memory tools |
| Live Excel workbook | Alfred `excel` MCP (excellm) |
| Power BI model | `powerbi-modeling-mcp` or `pbi` |
| GitHub PRs/issues | Alfred `github` MCP |
| Web research | Alfred Tavily (direct API) |
| Finance OneDrive files | Alfred `filesystem` MCP (scoped paths) |

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

**No API keys or accounts required** for core use. Optional opt-ins during setup:
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
