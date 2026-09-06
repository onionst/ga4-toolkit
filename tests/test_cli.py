from __future__ import annotations

import csv
import io
import json
import os
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from ga4_toolkit.cli import main
from ga4_toolkit.client import AnalyticsClient
from test_client import FakeSession


def sample_report():
    return {
        "dimensionHeaders": [{"name": "country"}],
        "metricHeaders": [{"name": "activeUsers"}],
        "rows": [{
            "dimensionValues": [{"value": "Spain"}],
            "metricValues": [{"value": "42"}],
        }],
        "rowCount": 3,
    }


class CLITests(unittest.TestCase):
    def invoke(self, args, payload=None):
        session = FakeSession(sample_report() if payload is None else payload)
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("ga4_toolkit.cli.AnalyticsClient", return_value=AnalyticsClient(session)):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                result = main(args)
        return result, stdout.getvalue(), stderr.getvalue(), session

    def test_all_report_commands_warn_without_corrupting_json(self):
        commands = [
            ["overview"], ["pages"], ["acquisition"], ["events"], ["realtime"],
            ["report", "--dimensions", "country", "--metrics", "activeUsers"],
        ]
        for command in commands:
            with self.subTest(command=command):
                code, output, errors, session = self.invoke(
                    [*command, "--property", "123", "--format", "json"]
                )
                self.assertEqual(code, 0)
                report = json.loads(output)
                self.assertEqual(report["property_id"], "123")
                self.assertTrue(report["truncated"])
                self.assertIn("1 of 3", errors)
                self.assertIn("/properties/123:", session.calls[0][1])

    def test_csv_remains_machine_readable_when_truncated(self):
        code, output, errors, _ = self.invoke(
            ["pages", "--property", "123", "--format", "csv"]
        )
        self.assertEqual(code, 0)
        self.assertEqual(list(csv.DictReader(io.StringIO(output))), [
            {"country": "Spain", "activeUsers": "42"},
        ])
        self.assertIn("Report truncated", errors)

    def test_table_warns_when_truncated(self):
        code, output, errors, _ = self.invoke(["pages", "--property", "123"])
        self.assertEqual(code, 0)
        self.assertIn("Spain", output)
        self.assertIn("1 of 3", errors)

    def test_implicit_property_is_identified_on_stderr(self):
        with patch.dict(os.environ, {"GA4_PROPERTY_ID": "98765"}):
            code, output, errors, session = self.invoke(
                ["metadata", "--format", "json"], {"dimensions": [], "metrics": []}
            )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["propertyId"], "98765")
        self.assertIn("using configured property 98765", errors)
        self.assertIn("/properties/98765/metadata", session.calls[0][1])

    def test_explicit_property_overrides_default_without_notice(self):
        with patch.dict(os.environ, {"GA4_PROPERTY_ID": "98765"}):
            code, output, errors, _ = self.invoke(
                ["pages", "--property", "123", "--format", "json"], {}
            )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["property_id"], "123")
        self.assertEqual(errors, "")

    def test_empty_explicit_property_does_not_use_default(self):
        with patch.dict(os.environ, {"GA4_PROPERTY_ID": "98765"}):
            code, output, errors, session = self.invoke(["pages", "--property", ""])
        self.assertEqual(code, 2)
        self.assertEqual(output, "")
        self.assertIn("must be numeric", errors)
        self.assertEqual(session.calls, [])


if __name__ == "__main__":
    unittest.main()
