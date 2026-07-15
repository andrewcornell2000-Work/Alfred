# Azure / Fabric authentication hard rules (Alfred)

Corporate Conditional Access bans device-code authentication. Alfred agents and docs must not steer anyone into it.

**Single source of truth for Fabric / Azure CLI auth policy.**

## Allowed (interactive)

- `az login` — **browser / company SSO / MAZAL only**
- Fabric REST via `az rest` after a valid browser login session (`az account show` succeeds)

## Forbidden

- Never: `az login --use-device-code`
- Never: “device-code login”, MSAL device-code, or any interactive device-code OAuth flow
- Never invent device-code as a “headless”, “no browser”, or “CI user” fallback
- Never auto-login during `setup.ps1`, install, or provision

## Agent behavior

1. Detect session with `az account show` (do not assume login).
2. If auth fails or there is no session: **tell the human** to run browser `az login` (company SSO). Do **not** run or suggest `--use-device-code`.
3. Prefer pointing humans at [COMMON-CLI.md § Authentication Recipes](COMMON-CLI.md#authentication-recipes) for the allowed commands only.

## Unattended / CI

Use only:

- Service principal (`az login --service-principal …`)
- Managed identity
- Workload identity

Never a user device-code flow.
