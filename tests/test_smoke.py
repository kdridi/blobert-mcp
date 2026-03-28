"""Smoke tests: verify the package imports and server can be instantiated."""


def test_package_imports():
    import blobert_mcp

    assert hasattr(blobert_mcp, "__version__")
    assert blobert_mcp.__version__ == "0.1.0"


def test_emulator_session_default_state():
    from blobert_mcp.emulator import EmulatorSession

    session = EmulatorSession()
    assert session.pyboy is None
    assert session.rom_loaded is False


def test_ping_tool():
    from blobert_mcp.server import ping

    result = ping()
    assert result == {"status": "ok", "rom_loaded": False}


def test_mcp_server_instance():
    from blobert_mcp.server import mcp

    assert mcp.name == "blobert-mcp"
