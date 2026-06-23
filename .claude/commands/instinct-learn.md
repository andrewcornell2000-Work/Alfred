---
description: Capture a reusable lesson from this session as a confidence-scored instinct.
---

# /instinct-learn

Extract the most useful reusable lesson from the current session and save it as
an instinct so future sessions start already knowing it.

## Steps

1. Look back over the session for a non-trivial pattern worth keeping:
   - an error → root cause → fix
   - a non-obvious debugging step or tool combo
   - a project convention or API quirk discovered
2. Phrase it as **trigger** ("when ...") + **guidance** ("do ...").
3. Pick scope:
   - `project` — specific to this repo's conventions
   - `global` — transfers to all work
4. Record it (re-recording the same trigger reinforces instead of duplicating):

```bash
python scripts/instinct-cli.py record \
  --domain "<short-domain>" \
  --trigger "when <situation>" \
  --guidance "do <action>" \
  --scope project
```

5. Confirm with `python scripts/instinct-cli.py status`.

Keep it concrete and reusable. One sharp instinct beats five vague ones.
