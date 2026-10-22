"""Optional MCP discovery: tools remain visible in every decision log."""

import asyncio
from functools import cached_property

from wallex_trading_agent.config import Settings


class McpToolCatalog:
    """Discover and expose names of tools published by the Wallex MCP server."""
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @cached_property
    def names(self) -> list[str]:
        if not self._settings.mcp_server_url:
            return []
        try:
            return asyncio.run(self._load_names())
        except Exception:  # MCP should never stop the risk-controlled REST fallback.
            return []

    async def _load_names(self) -> list[str]:
        from langchain_mcp_adapters.client import MultiServerMCPClient

        api_key = self._settings.wallex_api_key
        connection: dict[str, object] = {
            "transport": "streamable_http",
            "url": self._settings.mcp_server_url,
        }
        if api_key:
            connection["headers"] = {"x-api-key": api_key.get_secret_value()}
        client = MultiServerMCPClient({"wallex": connection})
        return sorted(tool.name for tool in await client.get_tools())
