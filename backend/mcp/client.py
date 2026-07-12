import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

_server_params = StdioServerParameters(
    command=sys.executable,
    args=["-m", "backend.mcp.server"],
    cwd=str(Path(__file__).parent.parent.parent),
)


async def _call(tool_name: str, arguments: dict):
    async with stdio_client(_server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            if result.isError:
                error_text = result.content[0].text if result.content else "unknown MCP error"
                raise RuntimeError(f"MCP tool '{tool_name}' failed: {error_text}")
            if not result.content:
                return []
            if len(result.content) == 1:
                raw = result.content[0].text
                try:
                    return json.loads(raw)
                except (json.JSONDecodeError, ValueError):
                    return raw
            # FastMCP serializes list elements as separate content items
            items = []
            for c in result.content:
                try:
                    items.append(json.loads(c.text))
                except (json.JSONDecodeError, ValueError):
                    items.append(c.text)
            return items


def call_mcp_tool(tool_name: str, arguments: dict):
    return asyncio.run(_call(tool_name, arguments))
