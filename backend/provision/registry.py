"""Unified capability registry for diagnostics and skill metadata."""

CAPABILITY_REQUIRES_LABELS = {
    "claude_cli": "Claude CLI",
    "codex_cli": "Codex CLI",
    "tavily_key": "Tavily API key",
    "mcp_excel": "Excel MCP",
    "mcp_powerbi": "Power BI MCP",
    "mcp_playwright": "Playwright MCP",
    "mcp_github": "GitHub MCP",
}

# Add new capabilities here or call register_tool() from a plugin.
TOOL_REGISTRY: dict[str, dict] = {
    "chat": {
        "name": "General Chat",
        "description": "Natural conversation, explanations, brainstorming, analysis",
        "category": "GENERAL",
        "provider": "claude",
        "requires": "claude_cli",
        "keywords": [],
        "examples": ["explain this", "what does X mean", "help me think through"],
    },
    "search": {
        "name": "Web Research",
        "description": "Live data — news, prices, versions, documentation, current events",
        "category": "SEARCH",
        "provider": "claude",
        "control_tower_provider": "tavily",
        "requires": "tavily_key",
        "keywords": ["latest", "current", "news", "price", "version", "today"],
        "examples": ["what's the latest Python version", "price of", "news about"],
    },
    "files": {
        "name": "File & System Operations",
        "description": "Read/write files, run scripts, inspect directories, execute commands",
        "category": "EXECUTE",
        "provider": "claude_code",
        "requires": "claude_cli",
        "keywords": ["file", "folder", "directory", "read", "write", "organise", "organize", "find file"],
        "examples": ["find my wages report", "organise this folder", "read this file"],
    },
    "code": {
        "name": "Code & Refactoring",
        "description": "Write, fix, refactor, test code in any language",
        "category": "CODE",
        "provider": "codex",
        "requires": "codex_cli",
        "keywords": ["code", "function", "bug", "test", "refactor", "script", "write a", "fix this"],
        "examples": ["fix this bug", "write a Python script to", "refactor this function"],
    },
    "excel": {
        "name": "Excel Automation",
        "description": "Live workbook editing — formulas, pivot tables, charts, VBA",
        "category": "EXECUTE",
        "provider": "claude_code",
        "requires": "mcp_excel",
        "keywords": ["excel", "spreadsheet", "workbook", "pivot", "chart", "formula", "vba", "macro"],
        "examples": ["check my Excel file", "add a pivot table", "update the formula in"],
    },
    "powerbi": {
        "name": "Power BI",
        "description": "DAX, model editing, relationships, visuals, Power Query diagnosis",
        "category": "POWERBI",
        "provider": "claude_code",
        "requires": "mcp_powerbi",
        "keywords": ["power bi", "powerbi", "dax", "power query", "visual", "report", "measure"],
        "examples": ["check my DAX measure", "why is Derrimut showing wrong", "add a measure for"],
    },
    "browser": {
        "name": "Browser Automation",
        "description": "Navigate websites, fill forms, scrape data, take screenshots",
        "category": "EXECUTE",
        "provider": "claude_code",
        "requires": "mcp_playwright",
        "keywords": ["browser", "website", "navigate", "scrape", "screenshot", "open", "go to"],
        "examples": ["open the website", "screenshot of", "scrape the table from"],
    },
    "github": {
        "name": "GitHub Operations",
        "description": "PRs, issues, diffs, commits, branches, repo management",
        "category": "EXECUTE",
        "provider": "claude_code",
        "requires": "mcp_github",
        "keywords": ["github", "pr", "pull request", "issue", "commit", "branch", "merge"],
        "examples": ["create a PR", "check my open issues", "review this diff"],
    },
    "office": {
        "name": "Office Documents",
        "description": "Word reports, PowerPoint decks, PDF extraction via python-docx/pptx",
        "category": "EXECUTE",
        "provider": "claude_code",
        "requires": "claude_cli",
        "keywords": ["word", "powerpoint", "pdf", "document", "presentation", "report", "docx", "pptx"],
        "examples": ["create a Word report", "build a PowerPoint from", "extract from this PDF"],
    },
}


def register_tool(
    key: str,
    name: str,
    description: str,
    category: str,
    provider: str,
    requires: str,
    keywords: "list[str] | None" = None,
    examples: "list[str] | None" = None,
    control_tower_provider: "str | None" = None,
) -> None:
    """Register a new capability. Appears in diagnostics and skill metadata."""
    entry = {
        "name": name,
        "description": description,
        "category": category,
        "provider": provider,
        "requires": requires,
        "keywords": keywords or [],
        "examples": examples or [],
    }
    if control_tower_provider:
        entry["control_tower_provider"] = control_tower_provider
    TOOL_REGISTRY[key] = entry


def iter_control_tower_capabilities() -> list[dict]:
    """Capability rows for `backend.cli diagnose`."""
    rows = []
    for tool in TOOL_REGISTRY.values():
        rows.append({
            "name": tool["name"],
            "provider": tool.get("control_tower_provider", tool["provider"]),
            "category": tool["category"],
            "description": tool["description"],
            "requires": tool["requires"],
        })
    return rows
