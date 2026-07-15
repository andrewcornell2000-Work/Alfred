# Safety gates for destructive tools

When adding MCP tools marked `destructive: true` in `alfred-tools.json`, document the risk here and in the tool's skill file.

Alfred no longer runs an interactive dispatch gate. These keywords are **documentation for skill authors and the growth loop** — agents should treat requests containing them as high-risk unless the user explicitly confirmed the action.

## DANGEROUS_KEYWORDS

Operations that require explicit user confirmation before execution:

- `delete`
- `remove`
- `overwrite`
- `credentials`
- `password`
- `entire onedrive`
- `all folders`
- `whole workspace`

## Forbidden auth (agent actions)

Device-code authentication is **forbidden** for Alfred agent actions and skill guidance:

- Never run or suggest `az login --use-device-code`
- Never recommend MSAL device-code / Graph MCP `--login` while `ms-365` is quarantined
- Interactive Azure: browser/SSO `az login` only; unattended: service principal / managed / workload identity

See `skills/_packs/common/AUTH-HARD-RULES.md`.

## When adding a destructive MCP

1. Set `"destructive": true` in `requirements/alfred-tools.json`.
2. Add a safety note to the relevant skill under `skills/`.
3. List any new high-risk phrases in this file if they are not covered above.
