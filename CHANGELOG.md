# Changelog

## 0.2.0 — 2026-09-06

First public release under the `ga4-toolkit` package name.

- CLI and MCP access to daily summaries, pages, acquisition, events, realtime
  activity, metadata, and custom GA4 reports.
- MCP reports and metadata require an explicit `property_id`. Omitted, null,
  and empty values are rejected instead of using a configured default.
- CLI commands identify the selected property on stderr when using a default.
- Report output includes `returned_row_count`, `truncated`, and `warnings`.
  CLI truncation warnings go to stderr so CSV and JSON output stay parseable.
- MIT license, an offline example, and CI on Python 3.11, 3.12, and 3.13.

### Upgrade

The `ga4` and `ga4-mcp` command names and configuration paths are unchanged.
The package name is now `ga4-toolkit`. Existing MCP callers must supply
`property_id` for every report and metadata request.
