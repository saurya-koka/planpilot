from __future__ import annotations

import asyncio

from mcp import (
    Client,
)

from backend.app.mcp_server import (
    mcp,
)


def test_mcp_client_discovers_planpilot_tools() -> None:
    async def run_test() -> None:
        async with Client(
            mcp
        ) as client:
            result = (
                await client.list_tools()
            )

            names = {
                tool.name
                for tool
                in result.tools
            }

            assert (
                "parse_trip_request"
                in names
            )

            assert (
                "search_planpilot_places"
                in names
            )

            assert (
                "check_planpilot_weather"
                in names
            )

            assert (
                "plan_itinerary"
                in names
            )

            assert (
                client.server_capabilities.tools
                is not None
            )

    asyncio.run(
        run_test()
    )


def test_mcp_client_calls_parse_tool() -> None:
    async def run_test() -> None:
        async with Client(
            mcp
        ) as client:
            result = (
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
                result.is_error
                is False
            )

            assert (
                result.structured_content
                is not None
            )

            structured = (
                result.structured_content
            )

            assert (
                structured[
                    "city"
                ]
                == "Boston"
            )

    asyncio.run(
        run_test()
    )


def test_mcp_client_reads_capabilities_resource() -> None:
    async def run_test() -> None:
        async with Client(
            mcp
        ) as client:
            resources = (
                await client.list_resources()
            )

            uris = {
                str(
                    resource.uri
                )
                for resource
                in resources.resources
            }

            assert (
                "planpilot://capabilities"
                in uris
            )

            result = (
                await client.read_resource(
                    "planpilot://capabilities"
                )
            )

            assert (
                len(
                    result.contents
                )
                >= 1
            )

            content = (
                result.contents[0]
            )

            text = getattr(
                content,
                "text",
                "",
            )

            assert (
                "PlanPilot MCP capabilities"
                in text
            )

    asyncio.run(
        run_test()
    )
