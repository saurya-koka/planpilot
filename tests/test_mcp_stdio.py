from __future__ import annotations

import asyncio
import os
import sys

from mcp import (
    Client,
    StdioServerParameters,
)
from mcp.client.stdio import (
    stdio_client,
)


def test_planpilot_mcp_stdio_subprocess() -> None:
    async def run_test() -> None:
        server_params = (
            StdioServerParameters(
                command=sys.executable,
                args=[
                    "-m",
                    "backend.app.mcp_server",
                ],
                env={
                    "PYTHONPATH": os.getcwd(),
                    "OPENAI_API_KEY": "",
                    "PLANPILOT_LIVE_WEATHER": "0",
                },
            )
        )

        transport = (
            stdio_client(
                server_params
            )
        )

        async with Client(
            transport
        ) as client:
            result = (
                await client.list_tools()
            )

            tool_names = {
                tool.name
                for tool
                in result.tools
            }

            assert (
                "parse_trip_request"
                in tool_names
            )

            assert (
                "search_planpilot_places"
                in tool_names
            )

            assert (
                "check_planpilot_weather"
                in tool_names
            )

            assert (
                "plan_itinerary"
                in tool_names
            )

            parsed = (
                await client.call_tool(
                    "parse_trip_request",
                    {
                        "text": (
                            "Plan a chill chicken "
                            "dinner in Boston for "
                            "two people under "
                            "120 dollars."
                        )
                    },
                )
            )

            assert (
                parsed.is_error
                is False
            )

            assert (
                parsed.structured_content
                is not None
            )

            assert (
                parsed.structured_content[
                    "city"
                ]
                == "Boston"
            )

    asyncio.run(
        run_test()
    )
