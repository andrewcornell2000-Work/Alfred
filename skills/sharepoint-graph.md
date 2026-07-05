# SharePoint & Microsoft 365 via Graph API (ms-365 MCP)

> **MCP:** `ms-365` (`@softeria/ms-365-mcp-server`)
> **Auth:** MSAL device-code — browser pop-up on first use, token cached locally after that. No API key needed.
> **Safety:** provisioned with `--read-only` by default. Remove that flag in `cursor/mcp.json` when you need to send mail or create files.
> **Covers:** SharePoint · OneDrive · Outlook mail · Calendar · Teams · Microsoft To-Do

---

## When to reach for this

Use `ms-365` when you want Cursor or Claude to:

- Find or read a file that lives in SharePoint or OneDrive — without downloading it manually
- Summarise or extract data from a document in a team site
- Check what meetings you have today or find a free slot
- Search your inbox for a thread without opening Outlook
- Pull a task list from Microsoft To-Do into a planning session

Do **not** use this for files that are already synced to your local machine (use `filesystem` MCP for that) or for reading local `.xlsx` files (use `excel` or `excel-mcp`).

---

## First-time setup

```
# Run this once — browser window opens, you sign in, token is cached
npx @softeria/ms-365-mcp-server --login
```

After that, Cursor/Claude picks it up automatically via the `ms-365` MCP entry. No key in `.env` needed.

---

## Routing cheat-sheet

| You want to… | Use |
|---|---|
| Read a file synced to your PC | `filesystem` MCP |
| Read a file that's ONLY in SharePoint/OneDrive | **`ms-365`** |
| Convert a SharePoint PDF to text | `ms-365` (read) → `markitdown` MCP |
| Query a local `.xlsx` export | `duckdb` or `excel` MCP |
| Check your local Outlook calendar | `outlook-calendar` MCP |
| Search cloud Outlook mail + calendar | **`ms-365`** |
| Open a browser and click around SharePoint | `playwright` MCP |

---

## Try asking (paste directly into Cursor)

### SharePoint / OneDrive — Files

**List files in a SharePoint folder:**
```
Use the ms-365 MCP to list all files in the "Finance Reports" document library on our SharePoint site. Show me file names and last-modified dates.
```

**Read a document:**
```
Use ms-365 to read the content of "Q2 Budget Review.docx" from the Finance SharePoint library and give me a 5-bullet summary.
```

**Search across OneDrive:**
```
Use ms-365 to search OneDrive for any Excel file with "labour" in the name modified in the last 30 days.
```

**Find a file and extract a table:**
```
Use ms-365 to read "Headcount Summary.xlsx" from SharePoint. Extract the table on the first sheet and show it as a markdown table here.
```

---

### Outlook — Mail

**Find a thread:**
```
Use ms-365 to search my Outlook inbox for emails from anyone at contractor.com received in the last 14 days. List sender, subject, and date.
```

**Summarise a thread:**
```
Use ms-365 to read the 5 most recent emails in my inbox with subject containing "DLP update" and give me a one-paragraph summary of what's been agreed.
```

**Draft a reply (write mode — remove --read-only first):**
```
Use ms-365 to draft a reply to the most recent email from Sarah Jones about the headcount review. Tell her the numbers are confirmed and the report will be ready Friday.
```

---

### Calendar

**What's on today:**
```
Use ms-365 to list my calendar events for today. Show time, title, and whether it's a Teams meeting.
```

**Find a free slot:**
```
Use ms-365 to find a 1-hour free slot in my calendar this week between 9am and 5pm for a meeting with the finance team.
```

**Create an event (write mode):**
```
Use ms-365 to create a calendar event: "Q2 Review" on Friday at 2pm for 1 hour with a Teams link.
```

---

### Microsoft To-Do / Tasks

**List tasks:**
```
Use ms-365 to list all incomplete tasks in my Microsoft To-Do "Work" list, sorted by due date.
```

**Create a task (write mode):**
```
Use ms-365 to add a task to my "Finance" To-Do list: "Upload Q2 actuals to SharePoint" due next Monday.
```

---

## Actionable patterns for finance work

### Pattern 1 — "Find the latest version without asking IT"
You can't remember which SharePoint folder has the current budget template. Instead of hunting through the browser:

```
Use ms-365 to search SharePoint for files named like "budget template" modified in 2026. List the site, folder, and last editor.
```

### Pattern 2 — "Summarise a document before downloading it"
Don't download a 40-page Word doc just to check if it has what you need:

```
Use ms-365 to read "Annual Report Draft v3.docx" from the Board Papers SharePoint library. Tell me: does it include a headcount section? If yes, paste that section here.
```

### Pattern 3 — "Pull data from SharePoint into a DuckDB query"
For a file too large to paste into chat, use ms-365 to read it, save the relevant rows to a local CSV, then query with DuckDB:

```
Step 1: Use ms-365 to read "Actuals_June.xlsx" from SharePoint and write the "Labour" sheet to a local file actuals_june_labour.csv.
Step 2: Use DuckDB to run: SELECT department, SUM(cost) FROM 'actuals_june_labour.csv' GROUP BY department ORDER BY SUM(cost) DESC.
```

### Pattern 4 — "Check if a report was circulated"
```
Use ms-365 to search my Outlook sent folder for any email with an attachment named like "Q2" sent in the last 7 days. Did I send the Q2 report to management?
```

---

## Permissions (what MSAL requests)

The server requests only the scopes needed for the tools you use. Default read-only scopes:

| Scope | Lets you |
|---|---|
| `Files.Read` | Read OneDrive and SharePoint files |
| `Mail.Read` | Read Outlook mail |
| `Calendars.Read` | Read your calendar |
| `Tasks.Read` | Read To-Do tasks |
| `User.Read` | Confirm your identity |

When you remove `--read-only`, write scopes (`Files.ReadWrite`, `Mail.Send`, `Calendars.ReadWrite`, `Tasks.ReadWrite`) are also requested.

To see exactly what your current configuration requests:
```
npx @softeria/ms-365-mcp-server --list-permissions
```

---

## Gotchas

- **Shared mailboxes / group calendars:** use `--org-mode` flag if you need to access calendars or mail beyond your own account
- **Synced files:** if the file is already in your local OneDrive sync folder, prefer `filesystem` MCP — it's faster and doesn't need a network call
- **Large files:** the MCP reads full content; for large Excel files use ms-365 to identify the file, then prefer DuckDB or excel-mcp for heavy querying
- **Write mode:** test in read-only first, confirm the right file/folder, then switch. Writes via Graph API are immediate — there is no undo from Cursor
- **Token expiry:** if you get an auth error after a long gap, re-run `npx @softeria/ms-365-mcp-server --login`
