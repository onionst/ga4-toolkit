from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from ga4_toolkit.client import (
    AnalyticsClient,
    AnalyticsError,
    flatten_report,
    read_config,
    resolve_property_id,
    save_default_property,
)


class FakeResponse:
    ok = True
    status_code = 200
    text = ""
    reason = "OK"

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return FakeResponse(self.payload)


class ClientTests(unittest.TestCase):
    def test_report_request_and_flattening(self):
        session = FakeSession(
            {
                "dimensionHeaders": [{"name": "country"}],
                "metricHeaders": [{"name": "activeUsers"}],
                "rows": [
                    {
                        "dimensionValues": [{"value": "Spain"}],
                        "metricValues": [{"value": "42"}],
                    }
                ],
                "rowCount": 1,
            }
        )
        client = AnalyticsClient(session=session)
        payload = client.run_report(
            property_id="properties/12345",
            dimensions=["country"],
            metrics=["activeUsers"],
            order_by_metric="activeUsers",
        )
        method, url, kwargs = session.calls[0]
        self.assertEqual(method, "POST")
        self.assertTrue(url.endswith("/properties/12345:runReport"))
        self.assertEqual(kwargs["json"]["limit"], "100")
        self.assertEqual(
            flatten_report(payload)["rows"],
            [{"country": "Spain", "activeUsers": "42"}],
        )

    def test_property_config_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"XDG_CONFIG_HOME": directory}, clear=False):
                path = save_default_property("properties/98765")
                self.assertTrue(path.exists())
                self.assertEqual(read_config()["default_property_id"], "98765")
                with patch.dict(os.environ, {"GA4_PROPERTY_ID": ""}, clear=False):
                    self.assertEqual(resolve_property_id(), "98765")

    def test_measurement_id_is_rejected(self):
        with self.assertRaises(AnalyticsError):
            resolve_property_id("G-ABC123")

    def test_invalid_metric_name_is_rejected(self):
        client = AnalyticsClient(session=FakeSession({}))
        with self.assertRaises(AnalyticsError):
            client.run_report(
                property_id="123",
                dimensions=["country"],
                metrics=["activeUsers;drop"],
            )

    def test_explicit_property_overrides_environment_and_saved_default(self):
        with patch.dict(os.environ, {"GA4_PROPERTY_ID": "222"}):
            with patch("ga4_toolkit.client.read_config", return_value={"default_property_id": "333"}):
                self.assertEqual(resolve_property_id("properties/111"), "111")
                self.assertEqual(resolve_property_id(), "222")

    def test_truncated_report_retains_total_and_returned_counts(self):
        report = flatten_report({
            "rowCount": 500,
            "rows": [{"dimensionValues": [], "metricValues": []}],
        })
        self.assertEqual(report["row_count"], 500)
        self.assertEqual(report["returned_row_count"], 1)
        self.assertTrue(report["truncated"])
        self.assertIn("1 of 500", report["warnings"][0])

    def test_complete_and_empty_reports_do_not_warn(self):
        for payload in ({}, {"rowCount": 0}, {"rowCount": 1, "rows": [{}]}):
            with self.subTest(payload=payload):
                report = flatten_report(payload)
                self.assertFalse(report["truncated"])
                self.assertEqual(report["warnings"], [])


if __name__ == "__main__":
    unittest.main()
