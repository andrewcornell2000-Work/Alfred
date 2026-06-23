---
description: Show Alfred's learned instincts (project + global) with confidence bars.
---

# /instinct-status

Display all learned instincts for the current project plus global instincts,
grouped by domain, with confidence bars and status (pending/active/strong).

Run:

```bash
python scripts/instinct-cli.py status
```

If the output is empty, Alfred hasn't learned anything for this project yet —
solve something, then use `/instinct-learn` to capture it.
