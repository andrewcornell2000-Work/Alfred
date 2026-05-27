# GitHub MCP

Use this skill for any task involving GitHub repositories: creating pull requests, managing issues,
searching code, reviewing diffs, or any interaction with github.com repositories.

## Tool: github MCP server

The GitHub MCP provides direct API access to GitHub. Requires a Personal Access Token configured
at install time.

## Core operations

### Pull requests
```
create_pull_request     — create a PR from a branch
list_pull_requests      — list open/closed PRs for a repo
get_pull_request        — get PR details, diff, review comments
merge_pull_request      — merge a PR
create_pull_request_review — leave a review
```

### Issues
```
create_issue            — open a new issue
list_issues             — list issues with filters
get_issue               — get issue details and comments
add_issue_comment       — comment on an issue
update_issue            — update labels, assignees, status
close_issue             — close an issue
```

### Repositories and code
```
search_repositories     — search GitHub for repos by query
get_file_contents       — read a file from any repo (with branch/SHA)
list_directory          — list files in a repo directory
search_code             — search code across GitHub
push_files              — push one or more files to a repo
create_branch           — create a new branch
```

### Commits and releases
```
list_commits            — list recent commits
create_tag              — tag a commit
```

## Typical PR workflow

1. `create_branch` — branch off main/master
2. `push_files` — commit the changes
3. `create_pull_request` — open the PR with title + body
4. Share the PR URL with the user

## When to use

- "Create a PR for my changes"
- "Open a GitHub issue for [bug]"
- "What issues are open in my repo?"
- "Search GitHub for [code/library]"
- "Review the diff on PR #[N]"
- "Push these files to the repo"

## Safety rules

- Always confirm repo owner/name before creating, merging, or pushing
- Never merge without user confirmation
- Read before write: get current file contents before overwriting
- PRs should always target the correct base branch (ask if unsure)
