# AGENTS.md — Coding Agent Guidelines

Instructions for Codex, Claude Code, and other coding agents working in this repository.

> Full guidelines: [`skills/karpathy-coding-guidelines.md`](skills/karpathy-coding-guidelines.md)  
> Source: [Andrej Karpathy — andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills/blob/main/CLAUDE.md)

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
- New tools with file-write or destructive capabilities must be documented in `requirements/safety-gates.md` before they are provisioned.
- Never auto-pull or auto-install tools without explicit user approval.
- When modifying executor/scoping prompts in skills, preserve minimum-scope principles in `skills/karpathy-coding-guidelines.md`.
- **Device-code auth is forbidden** for agent actions — browser/SSO `az login` only (see `skills/_packs/common/AUTH-HARD-RULES.md`). Do not suggest `az login --use-device-code` or MSAL device-code Graph login.

---

## Applies to

Coding, refactoring, debugging, architecture decisions, UI/app design, and Alfred self-improvement tasks.
