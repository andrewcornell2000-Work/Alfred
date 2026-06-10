# Active Projects
*Growth loop backlog — CLI, MCP, and agent skills (token efficiency + reasoning).*
*Last updated: 2026-06-10*

## LOOP MISSION TYPES (rotate daily)
1. **NEW MCP** — must reduce tokens OR improve structured reasoning; add to `cursor/mcp.json` + skill
2. **NEW CLI** — add to requirements manifests + how-to skill
3. **MCP HOW-TO** — deepen an existing MCP skill with worked examples
4. **CLI HOW-TO** — deepen gh/jq/pandoc/az/pbi/vd/claude/codex skill
5. **TOKEN EFFICIENCY** — improve `agent-token-efficiency.md` or related agent-* skill
6. **REASONING** — improve `agent-reasoning.md` or sequential-thinking guidance
7. **CONSOLIDATE** — merge duplicate tool skills
8. **ROUTING KEYWORDS** — small `TOOL_REGISTRY` edit when a new tool skill ships

## DONE
- [x] Alfred 2.0 — LeanCTX integrated via `lean-ctx bootstrap` after Alfred MCP provision (no API keys)
- [x] Full MCP catalog in `cursor/mcp.json` (13 servers) — provisions to Cursor + Claude + Codex
- [x] brave-search and exa removed; Tavily is the web-search path
- [x] Seed skills: `agent-token-efficiency.md`, `agent-reasoning.md`
- [x] Growth loop: must `write_file` before finishing; no analysis-only runs
- [x] Cross-tool skill sync includes `~/.codex/skills`

## MCP — deepen or add (token/reasoning angle)
- [ ] markitdown how-to skill with example prompts (saves tokens vs pasting binary docs)
- [ ] git MCP (`uvx mcp-server-git`) — structured diffs without dumping whole files
- [ ] SharePoint / Graph MCP (needs Azure app — research only until key available)

## CLI — deepen or add
- [ ] Codex vs Claude routing skill — when each saves tokens
- [ ] GitHub MCP skill — PR/issue workflows + gotchas
- [ ] `jq` skill — parse API JSON without pasting raw responses into chat

## AGENT SKILLS — token + reasoning
- [ ] Expand `agent-token-efficiency.md` with Power BI / DAX-specific examples
- [ ] Expand `agent-reasoning.md` with TaskKey / labour-planning reconciliation pattern
- [ ] Skill: when to use `duckdb` MCP vs pandas vs Excel MCP

## NOTES
- `cursor/mcp.json` is the portable template — safe to commit; installs nothing by itself
- `Provision-Cursor.ps1` registers MCPs for **Cursor + Claude Code + Codex** and syncs skills to all three
- `setup.ps1` / `Alfred-Install.exe` run provisioning automatically at end of install
- Never write secrets — use `${env:VAR}` + `_requires` in the template
- Finance/domain skills (cash-flow*, labour*, data-*, excel-financial*) are human-owned — loop must NOT edit them
