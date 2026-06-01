# Excel Financial Models

**Source:** https://github.com/anthropics/skills/blob/main/skills/xlsx/SKILL.md  
**Attribution:** Anthropic official skills repository.  
**Adapted for Alfred:** applies to any financial model, budget, forecast, or structured Excel deliverable.

---

## When This Skill Applies

Use when the task involves creating or editing an `.xlsx`, `.xlsm`, `.csv`, or `.tsv` file where the output is a financial model, report, or structured data deliverable — including:

- Building or editing budget/forecast models
- Creating variance analysis (actual vs budget)
- Labour cost models, headcount trackers, scenario planners
- Any spreadsheet where formulas must remain live and dynamic

---

## Non-Negotiable Standards

### Zero formula errors
Every delivered file must have **zero** `#REF!`, `#DIV/0!`, `#VALUE!`, `#N/A`, or `#NAME?` errors.

### Always use Excel formulas — never hardcode calculated values
```python
# ❌ WRONG — hardcodes the result, breaks when data changes
sheet['B10'] = 1_250_000

# ✅ CORRECT — formula stays live
sheet['B10'] = '=SUM(B2:B9)'
sheet['C5'] = '=(C4-C2)/C2'          # growth rate
sheet['D20'] = '=AVERAGE(D2:D19)'    # average
```

### Preserve existing templates
When editing an existing file: match its format, style, and conventions exactly. Never impose your own formatting.

---

## Financial Model Color Coding (Industry Standard)

| Colour | Use |
|--------|-----|
| **Blue text** (0,0,255) | Hardcoded inputs — numbers users change for scenarios |
| **Black text** (0,0,0) | All formulas and calculations |
| **Green text** (0,128,0) | Links pulling from other sheets within the same workbook |
| **Red text** (255,0,0) | External links to other files |
| **Yellow background** (255,255,0) | Key assumptions needing attention |

---

## Number Formatting Rules

| Type | Format |
|------|--------|
| Years | Text string — `"2024"` not `2,024` |
| Currency | `$#,##0` with unit in header — e.g. `Revenue ($mm)` |
| Zeros | `"$#,##0;($#,##0);-"` — display as `-` not `0` |
| Percentages | `0.0%` — one decimal place |
| Multiples | `0.0x` — e.g. EV/EBITDA |
| Negatives | Parentheses `(123)` — never minus `-123` |

---

## Formula Construction Rules

1. **All assumptions go in dedicated cells** — never hard-code a rate or multiple inside a formula
   - ✅ `=B5*(1+$B$6)` where `$B$6` is a labelled growth rate assumption
   - ❌ `=B5*1.05`

2. **Document any hardcoded values** with a source note:
   - `Source: FY2025 Budget, March 2025 Board Pack, Page 12`

3. **Pre-save formula checklist:**
   - [ ] Test 2–3 sample cell references pull correct values
   - [ ] Check column mapping (especially far-right columns past column Z)
   - [ ] Division by zero: verify denominators before `/`
   - [ ] Cross-sheet references use correct format: `Sheet1!A1`
   - [ ] No circular references

---

## Tool Selection

| Task | Tool |
|------|------|
| Data analysis, pivot, stats, bulk export | `pandas` |
| Formulas, formatting, charts, cell-level control | `openpyxl` |
| Live open Excel workbook (when Excel is running) | `excellm` MCP |

### openpyxl gotchas
- Cell indices are **1-based** (`row=1, col=1` = cell `A1`)
- `data_only=True` reads cached values but **destroys formulas on save** — never save after using it
- For large files use `read_only=True` (read) or `write_only=True` (create)

---

## Font & Presentation
- Use a consistent professional font throughout (Arial or Calibri)
- Column headers: bold
- Numbers: right-aligned
- Text: left-aligned
- Freeze top row on data sheets
