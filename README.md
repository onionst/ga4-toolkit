# GA4 Toolkit

[![CI](https://github.com/onionst/ga4-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/onionst/ga4-toolkit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A Python CLI and MCP server for read-only Google Analytics 4 reports. It provides
daily summaries, top pages, acquisition, events, realtime activity, metadata, and
custom reports through the Google Analytics Data and Admin APIs.

## Why use it?

Use the same reporting client in shell scripts and MCP conversations. Common
reports have ready-made commands, and results export as tables, JSON, or CSV.

This is an independent community project. Google maintains an
[official Analytics MCP server](https://github.com/googleanalytics/google-analytics-mcp).
This toolkit focuses on a small CLI and reusable report presets alongside MCP.
It is an early release; see the limits below before using it for bulk exports.

## Install

Requires Python 3.11 or newer and [uv](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/onionst/ga4-toolkit.git
cd ga4-toolkit
uv tool install .
ga4 --version
```

Installation provides the `ga4` and `ga4-mcp` commands. To update an existing installation after pulling
changes, run `uv tool install --force .`. There is no PyPI release; install from
this repository. If upgrading from the earlier private package, uninstall that
package first with `uv tool uninstall ga4-codex-toolkit`, then install this one.

Try the output format without a Google account:

```sh
uv sync --locked
uv run --locked python examples/offline_report.py
```

The example uses synthetic data and shows a report with two returned rows out of
three, including its truncation warning.

## Authentication

Enable the Google Analytics Data API and Google Analytics Admin API in the Google
Cloud project used for authentication. The Google identity must have access to
the target GA4 property; the Viewer role is sufficient for reports.

The client checks credentials in this order:

1. A service-account JSON key referenced by `GOOGLE_APPLICATION_CREDENTIALS`.
2. `~/.config/ga4-cli/google-credentials.json`, if present.
3. Google Application Default Credentials (ADC).

The second path respects `XDG_CONFIG_HOME` when set. Keep credential files outside
this repository. For a service account, grant its email access to the GA4 property
and point to its key:

```sh
export GOOGLE_APPLICATION_CREDENTIALS="/absolute/path/outside/repo/service-account.json"
ga4 properties
```

For user authentication, install the Google Cloud CLI and supply a Desktop OAuth
client JSON file from your Google Cloud project:

```sh
ga4 auth --client-id-file /absolute/path/outside/repo/client_secret.json
```

This invokes `gcloud auth application-default login` with the Analytics read-only
and Cloud Platform scopes. Follow the URL printed by gcloud; the browser does not
launch automatically unless you add `--launch-browser`. Reporting requests use
the `analytics.readonly` scope. No Analytics modification tools are exposed.

`ga4 doctor` checks access by listing properties. `ga4 auth` starts a new user
authentication flow or detects the dedicated service-account file; use `doctor`
to verify an existing ADC setup.

## CLI

Use the numeric GA4 property ID, not the `G-...` measurement ID. Pass `--property`
on every report to make the target explicit:

```sh
ga4 properties --format json
ga4 overview --property 123456789 --start 28daysAgo --end yesterday
ga4 pages --property 123456789 --limit 25
ga4 acquisition --property 123456789 --format csv
ga4 events --property 123456789 --format json
ga4 realtime --property 123456789 --dimensions country --metrics activeUsers,eventCount
ga4 report --property 123456789 --dimensions date,country --metrics sessions,activeUsers
ga4 metadata --property 123456789 --search session
```

Data commands support `--format table`, `json`, and `csv`. Historical reports
default to `28daysAgo` through `yesterday`. Custom reports also accept
`--dimension-filter-json`, `--metric-filter-json`, and `--order-by`.

An explicit property takes precedence over `GA4_PROPERTY_ID`, followed by an
optional default saved with `ga4 use PROPERTY_ID`. The default lives in
`~/.config/ga4-cli/config.json` and can be inspected with `ga4 config`. When
`--property` is omitted, the CLI prints the selected property on stderr before
querying it. An explicitly empty or invalid ID is rejected.

## MCP

Configure an MCP client to launch `ga4-mcp` over stdio. Use the absolute executable
path if the client does not inherit your shell's PATH:

```json
{
  "mcpServers": {
    "google-analytics": {
      "command": "/absolute/path/to/ga4-mcp"
    }
  }
}
```

The server exposes eight tools:

| Tool | Purpose |
| --- | --- |
| `ga4_list_properties` | Discover accessible properties |
| `ga4_overview` | Daily traffic, engagement, key events, and revenue |
| `ga4_top_pages` | Top page paths and titles |
| `ga4_acquisition` | Session channels and source/medium |
| `ga4_events` | Event counts, users, and values |
| `ga4_run_report` | Custom historical reports and filters |
| `ga4_realtime` | Realtime activity |
| `ga4_metadata` | Available dimensions and metrics |

`property_id` is required for every report and metadata call. Omitted, null, and
empty values are rejected; MCP reports do not fall back to environment variables
or saved defaults. Use property discovery when the target is unknown.

Example arguments for `ga4_top_pages`:

```json
{
  "property_id": "123456789",
  "start_date": "7daysAgo",
  "end_date": "yesterday",
  "limit": 25
}
```

MCP and CLI share authentication. The saved default property is a CLI convenience.

## Report completeness

JSON and MCP reports include the target `property_id`, total `row_count`,
`returned_row_count`, a `truncated` flag, and a `warnings` list. If the API reports
more rows than returned, the report is marked truncated. The CLI also writes the
warning to stderr in every output format, leaving stdout suitable for pipelines.

Increase `--limit` (or MCP `limit`) or narrow the report to retrieve more of the
matching rows. The daily overview uses a fixed 366-row cap; shorten its date range
or use a custom report when it is truncated. `truncated: false` only describes row
limits; Google may still apply thresholds or sampling, reflected in `metadata`.

## Limits

Report requests return at most 10,000 rows and do not paginate. Daily overview
requests cap results at 366 rows. Historical reports require 1–9 dimensions and
1–10 metrics; realtime reports require 1–4 of each. This version accepts simple
dimension and metric names; namespaced custom fields are not supported.

Metric/dimension compatibility, retention, and quotas are enforced by Google.
The client uses a 60-second request timeout and does not automatically retry API
failures. The CLI reports API errors on stderr and exits with status 2.

## Development

```sh
uv sync --locked
uv run --locked python -m unittest discover -s tests -v
uv build
```

Tests use fake API responses and a local MCP handshake. They require no Google
credentials and do not query Analytics.

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines and
[CHANGELOG.md](CHANGELOG.md) for release notes. Licensed under [MIT](LICENSE).
