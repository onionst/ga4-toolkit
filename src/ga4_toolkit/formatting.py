from __future__ import annotations

import csv
import io
import json
from typing import Any

from .client import flatten_report


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def render_rows(rows: list[dict[str, Any]], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(rows, ensure_ascii=False, indent=2)
    if not rows:
        return "No rows returned."
    columns = list(rows[0])
    if output_format == "csv":
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
        return stream.getvalue().rstrip("\r\n")
    widths = {
        column: max(len(column), *(len(_stringify(row.get(column))) for row in rows))
        for column in columns
    }
    header = "  ".join(column.ljust(widths[column]) for column in columns)
    divider = "  ".join("-" * widths[column] for column in columns)
    body = [
        "  ".join(_stringify(row.get(column)).ljust(widths[column]) for column in columns)
        for row in rows
    ]
    return "\n".join([header, divider, *body])


def render_report(payload: dict[str, Any], output_format: str) -> str:
    flattened = flatten_report(payload)
    if output_format == "json":
        return json.dumps(flattened, ensure_ascii=False, indent=2)
    return render_rows(flattened["rows"], output_format)


def render_metadata(payload: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(payload, ensure_ascii=False, indent=2)
    rows: list[dict[str, str]] = []
    for kind in ("dimensions", "metrics"):
        for item in payload.get(kind, []):
            rows.append(
                {
                    "type": kind[:-1],
                    "api_name": item.get("apiName", ""),
                    "ui_name": item.get("uiName", ""),
                    "category": item.get("category", ""),
                }
            )
    return render_rows(rows, output_format)
