from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .client import AnalyticsClient, flatten_report
from .presets import acquisition, events, overview, pages


mcp = FastMCP(
    "Google Analytics 4 (read-only)",
    instructions=(
        "Read-only access to GA4 reporting data. Use ga4_list_properties when the target "
        "property is ambiguous. Never combine or compare different properties unless the user "
        "explicitly requests it. Prefer a preset tool for common questions and ga4_run_report "
        "for custom dimensions and metrics."
    ),
    json_response=True,
)


def _client() -> AnalyticsClient:
    return AnalyticsClient()


@mcp.tool()
def ga4_list_properties() -> list[dict[str, str]]:
    """List every GA4 property accessible with the current read-only credentials."""
    return _client().list_properties()


@mcp.tool()
def ga4_overview(
    property_id: str | None = None,
    start_date: str = "28daysAgo",
    end_date: str = "yesterday",
) -> dict[str, Any]:
    """Return daily users, sessions, engagement, key events, and revenue."""
    return flatten_report(
        overview(
            _client(),
            property_id=property_id,
            start_date=start_date,
            end_date=end_date,
        )
    )


@mcp.tool()
def ga4_top_pages(
    property_id: str | None = None,
    start_date: str = "28daysAgo",
    end_date: str = "yesterday",
    limit: int = 25,
) -> dict[str, Any]:
    """Return top page paths and titles ordered by page views."""
    return flatten_report(
        pages(
            _client(),
            property_id=property_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
    )


@mcp.tool()
def ga4_acquisition(
    property_id: str | None = None,
    start_date: str = "28daysAgo",
    end_date: str = "yesterday",
    limit: int = 25,
) -> dict[str, Any]:
    """Return session channels and source/medium acquisition performance."""
    return flatten_report(
        acquisition(
            _client(),
            property_id=property_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
    )


@mcp.tool()
def ga4_events(
    property_id: str | None = None,
    start_date: str = "28daysAgo",
    end_date: str = "yesterday",
    limit: int = 25,
) -> dict[str, Any]:
    """Return top GA4 events, users, key events, and event values."""
    return flatten_report(
        events(
            _client(),
            property_id=property_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
    )


@mcp.tool()
def ga4_run_report(
    dimensions: list[str],
    metrics: list[str],
    property_id: str | None = None,
    start_date: str = "28daysAgo",
    end_date: str = "yesterday",
    limit: int = 100,
    dimension_filter: dict[str, Any] | None = None,
    metric_filter: dict[str, Any] | None = None,
    order_by_metric: str | None = None,
    descending: bool = True,
) -> dict[str, Any]:
    """Run a custom historical GA4 report with requested dimensions and metrics."""
    return flatten_report(
        _client().run_report(
            property_id=property_id,
            dimensions=dimensions,
            metrics=metrics,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            dimension_filter=dimension_filter,
            metric_filter=metric_filter,
            order_by_metric=order_by_metric,
            descending=descending,
        )
    )


@mcp.tool()
def ga4_realtime(
    dimensions: list[str] = ["country"],
    metrics: list[str] = ["activeUsers", "eventCount"],
    property_id: str | None = None,
    limit: int = 100,
    order_by_metric: str | None = None,
    descending: bool = True,
) -> dict[str, Any]:
    """Run a GA4 realtime report for activity from the last 30 minutes."""
    return flatten_report(
        _client().run_realtime_report(
            property_id=property_id,
            dimensions=dimensions,
            metrics=metrics,
            limit=limit,
            order_by_metric=order_by_metric,
            descending=descending,
        )
    )


@mcp.tool()
def ga4_metadata(
    property_id: str | None = None, search: str | None = None
) -> dict[str, Any]:
    """List compatible GA4 dimensions and metrics, optionally filtered by text."""
    return _client().get_metadata(property_id=property_id, search=search)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
