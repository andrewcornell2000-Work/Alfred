# AGENTS.md — Coding Agent Guidelines

Instructions for Codex, Claude Code, and Cursor agents working in this repository.

> Full guidelines: [`skills/karpathy-coding-guidelines.md`](skills/karpathy-coding-guidelines.md)

---

## Core Rules (apply to all coding tasks)

**1. Think before coding**
- State assumptions explicitly before starting. If uncertain, ask — don't proceed from unstated premises.
- If multiple interpretations exist, surface them rather than picking silently.

**2. Simplicity first**
- Write the minimum code that solves the problem. Nothing speculative.
- No unrequested features, abstractions, or configurability.
- If 200 lines could be 50, rewrite it.

**3. Surgical changes**
- Touch only what the task requires. Don't improve adjacent code.
- Match existing style. Note unrelated dead code — don't delete it unless asked.
- Every changed line must trace directly to the user's request.

**4. Goal-driven execution**
- Turn vague tasks into verifiable goals before writing code.
- For multi-step work, state a brief numbered plan with a verify step for each item.

---

## Alfred-specific rules

- Never add API keys, tokens, or credentials to committed files.
- New tools with file-write or destructive capabilities must be represented in the safety gate in `backend/main.py` (`DANGEROUS_KEYWORDS`) before dispatch is allowed.
- Never auto-pull or auto-install tools without explicit user approval.
- Execution scoping: minimize MCP usage, inspect minimum necessary scope, stop after diagnosis unless the user asked for fixes (see `CLAUDE.md`).

---

## Tooling

- **Native Cursor tools default** for repo work. See `cursor/rules/00-agent-tooling.mdc`.
- **Domain MCPs** only when the task requires them. See `skills/mcp-routing.md`.
- **lean-ctx optional** for large reads / compressed shell. See `skills/lean-ctx.md`.

---

## Repo structure

Where rules, skills, MCPs, and learning live: **`docs/ALFRED-STRUCTURE.md`**

---

## Applies to

Coding, refactoring, debugging, architecture decisions, UI/app design, and Alfred self-improvement tasks.
