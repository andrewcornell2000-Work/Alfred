# Alfred Pack

**Alfred is a global AI capability installer and updater** for Windows.

It installs and maintains reusable AI capabilities on your machine:

- **Skills** — domain how-tos synced globally
- **Rules** — Cursor agent rules, shared guidelines
- **MCP configurations** — Power BI, Excel, GitHub, browser, search, …
- **Prompts & workflows** — routing, learning, agent playbooks
- **Documentation & update mechanisms**

## Supported AI tools

| Tool | What Alfred configures |
|------|------------------------|
| **Cursor** | `~/.cursor/mcp.json`, skills, global rules |
| **Claude Code** | User-scope MCPs, `~/.claude/skills` |
| **Claude Desktop** | Connectors / MCP config |
| **Codex** | Global MCPs, `~/.codex/skills` |
| *Future apps* | Extend `Provision-Cursor.ps1` + registry |

**Security first:** per-user paths, no admin by default, secrets in local `.env` only.

## What you do day-to-day

**Work in Cursor or Claude** — capabilities are already provisioned globally.

## What Alfred does for you

| When | What |
|------|------|
| Fresh machine | Run `Alfred-Install.exe` once |
| Weekly / after updates | Re-run installer or `scripts\Alfred-Update.ps1` |
| "What's installed?" | `scripts\Validate-Install.ps1` or Alfred Control Tower |
| Learn new tools | Cursor Cloud Agent per `docs/CURSOR-CLOUD-AGENT.md` |
| Repair provision | `Provision-Cursor.ps1` |

Full install guide: **`docs/INSTALL.md`**

## Provision pipeline (single source of truth)

```
cursor/mcp.json          → MCP template (no secrets)
skills/*.md              → agent how-to skills
cursor/rules/*.mdc       → Cursor rules
Provision-Cursor.ps1     → global user-scope configs
scripts/Validate-Install.ps1 → post-install checks
scripts/Alfred-Update.ps1    → backup + pull + re-provision
```

## Learning & updates

**Cursor Cloud Agents** run the secure learning pipeline — see `docs/CURSOR-CLOUD-AGENT.md`.

Agents open PRs; you merge, then **Alfred.exe** or the update toast installs locally.

Review queue: `requirements/review-queue.json`

## Optional: Alfred CLI

`run-alfred.bat` — Control Tower, Dev Portal, updates. Not required for daily AI work.
