from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from ga4_toolkit.client import AnalyticsClient
from ga4_toolkit.mcp_server import ga4_overview
from test_client import FakeSession


class MCPServerTests(unittest.IsolatedAsyncioTestCase):
    async def test_server_exposes_only_expected_read_tools(self):
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "ga4_toolkit.mcp_server"],
        )
        async with stdio_client(parameters) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools = await session.list_tools()
        names = {tool.name for tool in tools.tools}
        for tool in tools.tools:
            if tool.name != "ga4_list_properties":
                self.assertIn("property_id", tool.inputSchema["required"])
        self.assertEqual(
            names,
            {
                "ga4_list_properties",
                "ga4_overview",
                "ga4_top_pages",
                "ga4_acquisition",
                "ga4_events",
                "ga4_run_report",
                "ga4_realtime",
                "ga4_metadata",
            },
        )

    async def test_reports_reject_missing_null_and_empty_property_over_stdio(self):
        with tempfile.TemporaryDirectory() as directory:
            parameters = StdioServerParameters(
                command=sys.executable,
                args=["-m", "ga4_toolkit.mcp_server"],
                env={
                    "GA4_PROPERTY_ID": "99999",
                    "GOOGLE_APPLICATION_CREDENTIALS": str(Path(directory) / "absent.json"),
                    "XDG_CONFIG_HOME": directory,
                },
            )
            async with stdio_client(parameters) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    for tool in tools.tools:
                        if tool.name == "ga4_list_properties":
                            continue
                        base = {"dimensions": ["country"], "metrics": ["activeUsers"]} if tool.name == "ga4_run_report" else {}
                        for supplied in ({}, {"property_id": None}, {"property_id": ""}):
                            with self.subTest(tool=tool.name, supplied=supplied):
                                result = await session.call_tool(tool.name, {**base, **supplied})
                                self.assertTrue(result.isError)
                                message = " ".join(getattr(item, "text", "") for item in result.content)
                                self.assertNotIn("Could not load Google credentials", message)

    def test_mcp_report_includes_truncation_warning(self):
        client = AnalyticsClient(FakeSession({"rowCount": 2, "rows": [{}]}))
        with patch("ga4_toolkit.mcp_server._client", return_value=client):
            report = ga4_overview(property_id="123")
        self.assertEqual(report["property_id"], "123")
        self.assertTrue(report["truncated"])
        self.assertIn("1 of 2", report["warnings"][0])


if __name__ == "__main__":
    unittest.main()
