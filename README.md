# GA4 Toolkit

A Python CLI and MCP server for read-only Google Analytics 4 reports. It provides
daily summaries, top pages, acquisition, events, realtime activity, metadata, and
custom reports through the Google Analytics Data and Admin APIs.

## Install

Requires Python 3.11 or newer and [uv](https://docs.astral.sh/uv/).

```sh
git clone git@github.com:onionst/ga4-codex-toolkit.git
cd ga4-codex-toolkit
uv tool install .
ga4 --version
```

The repository is private; cloning requires GitHub access. Installation provides
the `ga4` and `ga4-mcp` commands. To update an existing installation after pulling
changes, run `uv tool install --force .`.

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
`~/.config/ga4-cli/config.json` and can be inspected with `ga4 config`.

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

Pass `property_id` explicitly to every report and metadata call. Use property
discovery when the target is unknown. MCP and CLI share the same authentication
and local configuration.

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
