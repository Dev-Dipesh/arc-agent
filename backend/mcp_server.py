"""Arc Browser MCP Server — exposes shared Arc tools as MCP tools."""

import os

from mcp.server.fastmcp import FastMCP

from tool_registry import MCP_TOOL_FUNCTIONS

mcp = FastMCP(
    "arc-browser",
    host=os.getenv("ARC_MCP_HOST", "127.0.0.1"),
    port=int(os.getenv("ARC_MCP_PORT", "8765")),
    instructions=(
        "Tools for controlling Arc browser on macOS. "
        "Tabs belong to spaces; use space context when acting on tabs. "
        "Call arc_list_spaces first if available spaces are unknown. "
        "Always confirm with the user before calling arc_close_tab."
    ),
)

for _fn in MCP_TOOL_FUNCTIONS:
    mcp.tool()(_fn)


def main():
    transport = os.getenv("ARC_MCP_TRANSPORT", "stdio").strip().lower()
    if transport not in {"stdio", "sse", "streamable-http"}:
        raise ValueError(
            f"Invalid ARC_MCP_TRANSPORT='{transport}'. Use stdio, sse, or streamable-http."
        )
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
