from __future__ import annotations

import sys
import unittest

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


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


if __name__ == "__main__":
    unittest.main()
