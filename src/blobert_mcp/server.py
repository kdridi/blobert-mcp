"""MCP server for blobert-mcp."""

from mcp.server.fastmcp import FastMCP

from blobert_mcp.emulator import EmulatorSession

mcp = FastMCP("blobert-mcp")
session = EmulatorSession()


@mcp.tool()
def ping() -> dict:
    """Health check. Returns server status and whether a ROM is loaded."""
    return {"status": "ok", "rom_loaded": session.rom_loaded}


def main() -> None:
    """Entry point: run the MCP server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
