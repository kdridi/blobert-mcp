"""MCP server for blobert-mcp."""

from mcp.server.fastmcp import FastMCP

from blobert_mcp.emulator import EmulatorSession
from blobert_mcp.tools.disasm import register_disasm_tools
from blobert_mcp.tools.memory import register_memory_tools
from blobert_mcp.tools.session import register_session_tools
from blobert_mcp.tools.static import register_static_tools

mcp = FastMCP("blobert-mcp")
session = EmulatorSession()


@mcp.tool()
def ping() -> dict:
    """Health check. Returns server status and whether a ROM is loaded."""
    return {"status": "ok", "rom_loaded": session.rom_loaded}


register_session_tools(mcp, session)
register_static_tools(mcp, session)
register_memory_tools(mcp, session)
register_disasm_tools(mcp, session)


def main() -> None:
    """Entry point: run the MCP server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
