"""Arc Browser MCP Server — exposes shared Arc tools as MCP tools."""

from mcp.server.fastmcp import FastMCP

from tool_registry import MCP_TOOL_FUNCTIONS

mcp = FastMCP(
    "arc-browser",
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
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

