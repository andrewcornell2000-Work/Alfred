# COMMON-CLI (Alfred stub)

Alfred ships a **safe auth stub** for Fabric skills. Full upstream `COMMON-CLI` recipes (workspace discovery, LRO, etc.) are not bundled here; use skill-local patterns for those.

**Auth policy:** read [AUTH-HARD-RULES.md](AUTH-HARD-RULES.md) first. Device-code is forbidden.

## Authentication Recipes

Interactive and unattended recipes that Alfred agents may suggest. **Device-code is omitted on purpose.**

### Browser / SSO (interactive — default)

```bash
az login
az account show
```

Use company SSO / MAZAL when prompted. Never add `--use-device-code`.

If `az account show` fails, tell the human to run the commands above in their own terminal — do not invent a device-code workaround.

### Service principal (unattended / CI)

```bash
az login --service-principal \
  --username "$AZURE_CLIENT_ID" \
  --password "$AZURE_CLIENT_SECRET" \
  --tenant "$AZURE_TENANT_ID"
```

### Managed identity (Azure-hosted runners)

```bash
az login --identity
```

### Workload identity

Follow the host’s workload-identity federation docs (`az login --service-principal` with federated credentials). Do not fall back to device-code.

---

## Other COMMON-CLI sections

Anchors such as Finding Workspaces, `az rest`, LRO, and OneLake are **not** defined in this stub. Prefer recipes inside each Fabric skill’s `SKILL.md` / `references/`. When a skill link lands here for a non-auth section, stay in the calling skill’s local docs.
