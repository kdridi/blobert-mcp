# Security Policy

## Supported Versions

This project is pre-1.0 and in early development. Security fixes are applied
to the current `main` branch only.

| Version      | Supported          |
| ------------ | ------------------ |
| main branch  | :white_check_mark: |
| Older builds | :x:                |

## Reporting a Vulnerability

**Do not open a public issue for security vulnerabilities.**

Please report vulnerabilities through
[GitHub Security Advisories](https://github.com/kdridi/blobert-mcp/security/advisories/new).
This ensures the report is private and only visible to repository maintainers.

### Response Timeline

- **Acknowledgment:** Within 48 hours of the report.
- **Fix target:** Within 30 days of acknowledgment, depending on severity
  and complexity.

You will be credited in the fix unless you prefer to remain anonymous.

## Security Considerations

### ROM Files as Untrusted Input

blobert-mcp processes user-supplied Game Boy ROM files (`.gb`, `.gbc`, `.sgb`)
through [PyBoy](https://github.com/Baekalfen/PyBoy). ROM files should be
treated as **untrusted input**. Malformed or adversarial ROM data could
potentially trigger unexpected behavior in the emulator.

If you discover a way to exploit ROM processing to achieve code execution,
information disclosure, or denial of service, please report it through the
process above.
