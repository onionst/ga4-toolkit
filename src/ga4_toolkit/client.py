from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Iterable

import google.auth
from google.auth.exceptions import DefaultCredentialsError
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account


ANALYTICS_READONLY_SCOPE = "https://www.googleapis.com/auth/analytics.readonly"
DATA_API_ROOT = "https://analyticsdata.googleapis.com/v1beta"
ADMIN_API_ROOT = "https://analyticsadmin.googleapis.com/v1beta"
DEFAULT_TIMEOUT_SECONDS = 60
MAX_ROWS = 10_000


class AnalyticsError(RuntimeError):
    """Base error for GA4 toolkit failures."""


class AnalyticsAuthError(AnalyticsError):
    """Raised when Google Application Default Credentials are unavailable."""


class AnalyticsAPIError(AnalyticsError):
    """Raised when a Google Analytics API request fails."""


def config_path() -> Path:
    root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "ga4-cli" / "config.json"


def default_service_account_path() -> Path:
    return config_path().with_name("google-credentials.json")


def read_config() -> dict[str, Any]:
    path = config_path()
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AnalyticsError(f"Could not read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AnalyticsError(f"Invalid configuration in {path}: expected an object")
    return value


def save_default_property(property_id: str) -> Path:
    normalized = normalize_property_id(property_id)
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"default_property_id": normalized}, indent=2) + "\n",
        encoding="utf-8",
    )
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def normalize_property_id(property_id: str | int) -> str:
    value = str(property_id).strip()
    if value.startswith("properties/"):
        value = value.split("/", 1)[1]
    if not re.fullmatch(r"[0-9]+", value):
        raise AnalyticsError(
            "GA4 property ID must be numeric (not the G-XXXXXXXX measurement ID)"
        )
    return value


def resolve_property_id(property_id: str | int | None = None) -> str:
    if property_id not in (None, ""):
        return normalize_property_id(property_id)
    env_value = os.environ.get("GA4_PROPERTY_ID")
    if env_value:
        return normalize_property_id(env_value)
    saved = read_config().get("default_property_id")
    if saved:
        return normalize_property_id(saved)
    raise AnalyticsError(
        "No GA4 property selected. Run `ga4 properties`, then `ga4 use PROPERTY_ID`, "
        "or set GA4_PROPERTY_ID."
    )


def validate_names(values: Iterable[str], kind: str, maximum: int) -> list[str]:
    names = [value.strip() for value in values if value and value.strip()]
    if not names:
        raise AnalyticsError(f"At least one {kind} is required")
    if len(names) > maximum:
        raise AnalyticsError(f"At most {maximum} {kind}s are allowed")
    for name in names:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name):
            raise AnalyticsError(f"Invalid {kind} name: {name!r}")
    return names


def validate_limit(limit: int) -> int:
    if limit < 1 or limit > MAX_ROWS:
        raise AnalyticsError(f"limit must be between 1 and {MAX_ROWS}")
    return limit


class AnalyticsClient:
    def __init__(self, session: AuthorizedSession | None = None) -> None:
        self._session = session

    def _get_session(self) -> AuthorizedSession:
        if self._session is not None:
            return self._session
        credential_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if not credential_file and default_service_account_path().is_file():
            credential_file = str(default_service_account_path())
        try:
            if credential_file:
                credentials = service_account.Credentials.from_service_account_file(
                    credential_file, scopes=[ANALYTICS_READONLY_SCOPE]
                )
            else:
                credentials, _ = google.auth.default(
                    scopes=[ANALYTICS_READONLY_SCOPE]
                )
        except DefaultCredentialsError as exc:
            raise AnalyticsAuthError(
                "Google Application Default Credentials were not found. Run `ga4 auth` "
                "or set GOOGLE_APPLICATION_CREDENTIALS to a read-only service-account key."
            ) from exc
        except (OSError, ValueError) as exc:
            raise AnalyticsAuthError(
                f"Could not load Google credentials from {credential_file}: {exc}"
            ) from exc
        self._session = AuthorizedSession(credentials)
        return self._session

    def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        session = self._get_session()
        try:
            response = session.request(
                method,
                url,
                params=params,
                json=body,
                timeout=DEFAULT_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            raise AnalyticsAPIError(f"Google Analytics request failed: {exc}") from exc
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        if not response.ok:
            detail = payload.get("error", {}).get("message") if isinstance(payload, dict) else None
            detail = detail or response.text or response.reason
            raise AnalyticsAPIError(
                f"Google Analytics API returned HTTP {response.status_code}: {detail}"
            )
        if not isinstance(payload, dict):
            raise AnalyticsAPIError("Google Analytics API returned an unexpected response")
        return payload

    def list_properties(self) -> list[dict[str, str]]:
        items: list[dict[str, str]] = []
        page_token: str | None = None
        while True:
            params = {"pageSize": 200}
            if page_token:
                params["pageToken"] = page_token
            payload = self._request(
                "GET", f"{ADMIN_API_ROOT}/accountSummaries", params=params
            )
            for account in payload.get("accountSummaries", []):
                account_name = account.get("displayName", "")
                account_id = str(account.get("account", "")).removeprefix("accounts/")
                for prop in account.get("propertySummaries", []):
                    items.append(
                        {
                            "account_id": account_id,
                            "account_name": account_name,
                            "property_id": str(prop.get("property", "")).removeprefix(
                                "properties/"
                            ),
                            "property_name": prop.get("displayName", ""),
                            "property_type": prop.get("propertyType", ""),
                        }
                    )
            page_token = payload.get("nextPageToken")
            if not page_token:
                break
        return items

    def run_report(
        self,
        *,
        dimensions: Iterable[str],
        metrics: Iterable[str],
        start_date: str = "28daysAgo",
        end_date: str = "yesterday",
        property_id: str | int | None = None,
        limit: int = 100,
        dimension_filter: dict[str, Any] | None = None,
        metric_filter: dict[str, Any] | None = None,
        order_by_metric: str | None = None,
        descending: bool = True,
    ) -> dict[str, Any]:
        prop = resolve_property_id(property_id)
        dimension_names = validate_names(dimensions, "dimension", 9)
        metric_names = validate_names(metrics, "metric", 10)
        body: dict[str, Any] = {
            "dateRanges": [{"startDate": start_date, "endDate": end_date}],
            "dimensions": [{"name": name} for name in dimension_names],
            "metrics": [{"name": name} for name in metric_names],
            "limit": str(validate_limit(limit)),
            "returnPropertyQuota": True,
        }
        if dimension_filter:
            body["dimensionFilter"] = dimension_filter
        if metric_filter:
            body["metricFilter"] = metric_filter
        if order_by_metric:
            if order_by_metric not in metric_names:
                raise AnalyticsError("order_by_metric must be one of the requested metrics")
            body["orderBys"] = [
                {"metric": {"metricName": order_by_metric}, "desc": descending}
            ]
        payload = self._request(
            "POST", f"{DATA_API_ROOT}/properties/{prop}:runReport", body=body
        )
        payload["propertyId"] = prop
        payload["requestedDateRange"] = {"startDate": start_date, "endDate": end_date}
        return payload

    def run_realtime_report(
        self,
        *,
        dimensions: Iterable[str],
        metrics: Iterable[str],
        property_id: str | int | None = None,
        limit: int = 100,
        order_by_metric: str | None = None,
        descending: bool = True,
    ) -> dict[str, Any]:
        prop = resolve_property_id(property_id)
        dimension_names = validate_names(dimensions, "dimension", 4)
        metric_names = validate_names(metrics, "metric", 4)
        body: dict[str, Any] = {
            "dimensions": [{"name": name} for name in dimension_names],
            "metrics": [{"name": name} for name in metric_names],
            "limit": str(validate_limit(limit)),
            "returnPropertyQuota": True,
        }
        if order_by_metric:
            if order_by_metric not in metric_names:
                raise AnalyticsError("order_by_metric must be one of the requested metrics")
            body["orderBys"] = [
                {"metric": {"metricName": order_by_metric}, "desc": descending}
            ]
        payload = self._request(
            "POST", f"{DATA_API_ROOT}/properties/{prop}:runRealtimeReport", body=body
        )
        payload["propertyId"] = prop
        return payload

    def get_metadata(
        self,
        *,
        property_id: str | int | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        prop = resolve_property_id(property_id)
        payload = self._request(
            "GET", f"{DATA_API_ROOT}/properties/{prop}/metadata"
        )
        if search:
            needle = search.casefold()
            for key in ("dimensions", "metrics"):
                payload[key] = [
                    item
                    for item in payload.get(key, [])
                    if needle
                    in " ".join(
                        str(item.get(field, ""))
                        for field in ("apiName", "uiName", "description", "category")
                    ).casefold()
                ]
        payload["propertyId"] = prop
        return payload


def flatten_report(payload: dict[str, Any]) -> dict[str, Any]:
    dimension_headers = [item.get("name", "") for item in payload.get("dimensionHeaders", [])]
    metric_headers = [item.get("name", "") for item in payload.get("metricHeaders", [])]
    columns = dimension_headers + metric_headers
    rows: list[dict[str, str]] = []
    for row in payload.get("rows", []):
        values = [item.get("value", "") for item in row.get("dimensionValues", [])]
        values.extend(item.get("value", "") for item in row.get("metricValues", []))
        rows.append(dict(zip(columns, values)))
    row_count = int(payload.get("rowCount", len(rows)))
    truncated = row_count > len(rows)
    warnings = []
    if truncated:
        warnings.append(
            f"Report truncated: returned {len(rows)} of {row_count} rows. "
            "Increase the limit (up to 10000) or narrow the report; "
            "automatic pagination is not supported."
        )
    return {
        "property_id": payload.get("propertyId"),
        "date_range": payload.get("requestedDateRange"),
        "columns": columns,
        "rows": rows,
        "row_count": row_count,
        "returned_row_count": len(rows),
        "truncated": truncated,
        "warnings": warnings,
        "metadata": payload.get("metadata", {}),
        "property_quota": payload.get("propertyQuota", {}),
    }
