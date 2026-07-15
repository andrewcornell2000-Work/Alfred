# SharePoint & Microsoft 365 (Graph MCP — quarantined)

> **Status:** **QUARANTINED** under corporate Conditional Access.
> **MCP:** `ms-365` (`@softeria/ms-365-mcp-server`) is **not** in default `cursor/mcp.json` / provision.
> **Why:** Current login path uses **MSAL device-code**, which is **TENANT-FORBIDDEN**. See [AUTH-HARD-RULES.md](_packs/common/AUTH-HARD-RULES.md).
> **Do not** re-enable or run `--login` until a non–device-code auth path exists.

---

## What to use instead

| You want to… | Use |
|---|---|
| Read a file synced to your PC (OneDrive / SharePoint sync) | `filesystem` MCP (finance OneDrive root) or native Read |
| Open / query a local `.xlsx` | `excel` or `excel-mcp` |
| Check local Outlook calendar | `outlook-calendar` MCP |
| Fabric / Power BI via Azure CLI | browser/SSO `az login` + Fabric skills ([AUTH-HARD-RULES.md](_packs/common/AUTH-HARD-RULES.md)) |
| Browse a SharePoint site in a real browser | `playwright` MCP (manual human SSO in the browser — not device-code CLI) |

Prefer syncing the library to OneDrive and reading from disk over remote Graph calls while this MCP stays quarantined.

---

## Agent rules

1. Do **not** instruct users to `npx @softeria/ms-365-mcp-server --login` or any device-code Graph login.
2. Do **not** add `ms-365` back to default provision without an approved non–device-code auth design.
3. If the user asks for cloud-only SharePoint/OneDrive content that is not synced locally, explain the quarantine and offer sync/`filesystem` or human browser access.

---

## Historical note

Older Alfred packs provisioned `ms-365` with `--read-only`. Re-running `Provision-Cursor.ps1` removes the retired server from Cursor/Claude configs via `_retiredServers`.
