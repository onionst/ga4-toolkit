from __future__ import annotations

from typing import Any

from .client import AnalyticsClient


def overview(
    client: AnalyticsClient,
    *,
    property_id: str | None = None,
    start_date: str = "28daysAgo",
    end_date: str = "yesterday",
) -> dict[str, Any]:
    return client.run_report(
        property_id=property_id,
        dimensions=["date"],
        metrics=[
            "activeUsers",
            "newUsers",
            "sessions",
            "engagedSessions",
            "engagementRate",
            "keyEvents",
            "totalRevenue",
        ],
        start_date=start_date,
        end_date=end_date,
        limit=366,
    )


def pages(
    client: AnalyticsClient,
    *,
    property_id: str | None = None,
    start_date: str = "28daysAgo",
    end_date: str = "yesterday",
    limit: int = 25,
) -> dict[str, Any]:
    return client.run_report(
        property_id=property_id,
        dimensions=["pagePath", "pageTitle"],
        metrics=["screenPageViews", "activeUsers", "sessions", "engagementRate"],
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        order_by_metric="screenPageViews",
    )


def acquisition(
    client: AnalyticsClient,
    *,
    property_id: str | None = None,
    start_date: str = "28daysAgo",
    end_date: str = "yesterday",
    limit: int = 25,
) -> dict[str, Any]:
    return client.run_report(
        property_id=property_id,
        dimensions=["sessionDefaultChannelGroup", "sessionSourceMedium"],
        metrics=["sessions", "activeUsers", "engagedSessions", "keyEvents"],
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        order_by_metric="sessions",
    )


def events(
    client: AnalyticsClient,
    *,
    property_id: str | None = None,
    start_date: str = "28daysAgo",
    end_date: str = "yesterday",
    limit: int = 25,
) -> dict[str, Any]:
    return client.run_report(
        property_id=property_id,
        dimensions=["eventName"],
        metrics=["eventCount", "totalUsers", "keyEvents", "eventValue"],
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        order_by_metric="eventCount",
    )
