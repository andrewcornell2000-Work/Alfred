# Office Mastery

Use this skill for work involving Microsoft Office documents, reporting packs, executive summaries, slide decks, PDF source material, Excel workbooks, and Power BI deliverables.

## Goal

Alfred should behave like an analyst, automation engineer, and document producer in one loop:

1. Understand the audience and business objective.
2. Inspect only the files or live apps needed for the task.
3. Produce a polished artifact or a precise change plan.
4. Preserve source files unless the user explicitly asks for edits.

## Capability Map

| Domain | Primary tool path | Use for |
|---|---|---|
| Excel live workbooks | `excel` MCP / `excellm` | Open workbook inspection, formulas, tables, pivots, formatting, charts, VBA |
| Excel offline files | `openpyxl`, `pandas` | XLSX cleanup, transformations, exports, repeatable data prep |
| Power BI models | `powerbi-modeling-mcp` | DAX, measures, columns, tables, relationships, model metadata |
| Power BI visuals | `pbi-cli` | Creating and editing visuals while Power BI Desktop is open |
| Word documents | `python-docx` | Reports, proposals, briefs, templates, structured deliverables |
| PowerPoint decks | `python-pptx` | Slide decks, executive packs, analysis presentations |
| PDFs | `pypdf` | Extracting, comparing, splitting, merging, summarizing source documents |
| Browser evidence | `playwright` MCP | Screenshots, web research, form workflows, evidence capture |

## Working Rules

- Ask for or infer the target audience before polishing a report or deck.
- Prefer structured outputs: headings, tables, named sections, and clear recommendations.
- For edits to existing files, create a backup or save a new version unless the user explicitly asks to overwrite.
- For Excel and Power BI, inspect workbook/model structure before changing formulas, DAX, relationships, or visuals.
- For Power Query or folder-combine errors, inspect query steps before source files.
- For PDF extraction, preserve citations such as page numbers when producing summaries.
- For executive documents, keep the first page or first slide decision-ready: answer, implication, next action.

## Safety

Office workflows can overwrite valuable business files. Treat workbook writes, model edits, document rewrites, and deck generation as destructive unless the output is clearly a new file.

Before destructive edits:

1. Confirm the target file or live app.
2. State the intended change.
3. Prefer a backup/new copy.
4. Stop if credentials, private tokens, or unrelated personal files are discovered.
