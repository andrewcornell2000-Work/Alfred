"""
Power Query (M expression) helpers for Alfred.

Talks to the live Excel Application via COM automation (win32com).
Excel must be running with the target workbook open.

All public functions return a dict:
  {"success": True,  ...result fields... }
  {"success": False, "error": "human-readable message"}
"""
from __future__ import annotations

import re


# ── COM plumbing ──────────────────────────────────────────────────────────────


def _xl_app():
    """Return a running Excel.Application COM object, or raise RuntimeError."""
    try:
        import win32com.client  # type: ignore
    except ImportError:
        raise RuntimeError(
            "pywin32 is not installed.\n"
            "Fix: activate Alfred's .venv, then run:  pip install pywin32"
        )
    try:
        return win32com.client.GetObject(Class="Excel.Application")
    except Exception as exc:
        raise RuntimeError(
            f"Excel is not running (or not accessible via COM): {exc}\n"
            "Open your workbook in Excel first, then retry."
        )


def _get_workbook(xl, wb_name: str | None):
    """
    Return the named workbook, or the active workbook when wb_name is None.
    Matching is case-insensitive and partial (matches on Name or FullName).
    """
    wbs = list(xl.Workbooks)
    if not wbs:
        raise RuntimeError("No workbooks are open in Excel.")

    if wb_name:
        needle = wb_name.lower()
        for wb in wbs:
            if needle in wb.Name.lower() or needle in wb.FullName.lower():
                return wb
        names = ", ".join(wb.Name for wb in wbs)
        raise RuntimeError(
            f"Workbook matching '{wb_name}' not found.\n"
            f"Open workbooks: {names}"
        )

    active = xl.ActiveWorkbook
    if active is None:
        raise RuntimeError("No active workbook. Open or activate a workbook in Excel.")
    return active


def _queries(wb) -> list:
    """Return list of WorkbookQuery COM objects, or raise RuntimeError."""
    try:
        qs = list(wb.Queries)  # COM collection — iterates WorkbookQuery objects
    except Exception as exc:
        raise RuntimeError(
            f"Queries collection unavailable: {exc}\n"
            "Power Query requires Excel 2016 or later."
        )
    return qs


# ── Public helpers ────────────────────────────────────────────────────────────


def list_queries(wb_name: str | None = None) -> dict:
    """
    List all Power Query queries in the workbook.

    Returns:
        {"success": True, "workbook": str, "queries": [{"name": str, "description": str}, ...]}
    """
    try:
        xl = _xl_app()
        wb = _get_workbook(xl, wb_name)
        qs = _queries(wb)
        rows = []
        for q in qs:
            rows.append(
                {
                    "name": q.Name,
                    "description": _safe_attr(q, "Description", ""),
                }
            )
        return {"success": True, "workbook": wb.Name, "queries": rows}
    except RuntimeError as exc:
        return {"success": False, "error": str(exc)}


def get_query(query_name: str, wb_name: str | None = None) -> dict:
    """
    Return the M expression for a named query.

    Returns:
        {"success": True, "name": str, "formula": str, "workbook": str}
    """
    try:
        xl = _xl_app()
        wb = _get_workbook(xl, wb_name)
        qs = _queries(wb)
        for q in qs:
            if q.Name.lower() == query_name.lower():
                return {
                    "success": True,
                    "name": q.Name,
                    "formula": q.Formula,
                    "workbook": wb.Name,
                }
        available = ", ".join(q.Name for q in qs) or "(none)"
        return {
            "success": False,
            "error": f"Query '{query_name}' not found.\nAvailable: {available}",
        }
    except RuntimeError as exc:
        return {"success": False, "error": str(exc)}


def set_query(query_name: str, m_expr: str, wb_name: str | None = None) -> dict:
    """
    Replace the M expression for a named query, or create it if absent.

    Returns:
        {"success": True, "name": str, "action": "updated"|"created", "workbook": str}
    """
    try:
        xl = _xl_app()
        wb = _get_workbook(xl, wb_name)
        qs = _queries(wb)
        for q in qs:
            if q.Name.lower() == query_name.lower():
                q.Formula = m_expr
                return {
                    "success": True,
                    "name": q.Name,
                    "action": "updated",
                    "workbook": wb.Name,
                }
        # Query doesn't exist — create it
        wb.Queries.Add(query_name, m_expr)
        return {
            "success": True,
            "name": query_name,
            "action": "created",
            "workbook": wb.Name,
        }
    except RuntimeError as exc:
        return {"success": False, "error": str(exc)}
    except Exception as exc:
        return {"success": False, "error": f"COM error writing query: {exc}"}


def refresh_query(query_name: str | None = None, wb_name: str | None = None) -> dict:
    """
    Refresh one query (by name) or all queries in the workbook.

    Returns:
        {"success": True, "refreshed": [str, ...], "workbook": str}
    """
    try:
        xl = _xl_app()
        wb = _get_workbook(xl, wb_name)
        qs = _queries(wb)
        refreshed: list[str] = []
        errors: list[str] = []

        targets = (
            [q for q in qs if q.Name.lower() == query_name.lower()]
            if query_name
            else list(qs)
        )

        if not targets:
            if query_name:
                available = ", ".join(q.Name for q in qs) or "(none)"
                return {
                    "success": False,
                    "error": f"Query '{query_name}' not found.\nAvailable: {available}",
                }
            return {"success": False, "error": "No queries found in this workbook."}

        for q in targets:
            try:
                q.Refresh()
                refreshed.append(q.Name)
            except Exception as qe:
                errors.append(f"{q.Name}: {qe}")

        if errors and not refreshed:
            return {"success": False, "error": "\n".join(errors)}

        result: dict = {"success": True, "refreshed": refreshed, "workbook": wb.Name}
        if errors:
            result["warnings"] = errors
        return result
    except RuntimeError as exc:
        return {"success": False, "error": str(exc)}


# ── Utilities ─────────────────────────────────────────────────────────────────


def _safe_attr(obj, attr: str, default=""):
    """Read a COM attribute without raising on missing/null."""
    try:
        val = getattr(obj, attr, default)
        return val if val is not None else default
    except Exception:
        return default
