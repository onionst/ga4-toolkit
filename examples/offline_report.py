"""Show the report format using synthetic data; no credentials or API calls."""

from ga4_toolkit.formatting import render_report


report = {
    "propertyId": "123456789",
    "requestedDateRange": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
    "dimensionHeaders": [{"name": "country"}],
    "metricHeaders": [{"name": "activeUsers"}],
    "rows": [
        {"dimensionValues": [{"value": "Spain"}], "metricValues": [{"value": "42"}]},
        {"dimensionValues": [{"value": "Portugal"}], "metricValues": [{"value": "17"}]},
    ],
    "rowCount": 3,
}

print(render_report(report, "json"))
