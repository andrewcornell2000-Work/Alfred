# lean-ctx — Optional Context Compression

Native Claude Code tools are the default. lean-ctx is optional for token savings on large reads and noisy shell output.

## Default
- **Read / Grep / Bash / Edit** → native tools
- **Excel / Power BI / GitHub** → Alfred domain MCPs

## When lean-ctx helps
| Situation | Tool |
|-----------|------|
| Large file overview | `ctx_read(path, "map")` |
| Targeted region | `ctx_read(path, "lines:N-M")` |
| Re-read after edit | `ctx_read(path, "diff")` |
| Repo search | `ctx_search(pattern, path)` |
| Noisy command output | `lean-ctx -c "<cmd>"` |
| Cross-session facts | `ctx_knowledge` |

## Bail-out
If lean-ctx errors or exceeds ~5 seconds, use native tools for the rest of the turn. Do not call `ctx_overview` on every session start.

Full reference: `skills/lean-ctx.md`
