# ADR 0003: CSV Formula Injection (CSV Injection) Mitigation

## Status
Accepted

## Context
Analysts frequently export dataset observations into desktop spreadsheet programs (Microsoft Excel, LibreOffice Calc). If a cell begins with characters such as `=`, `+`, `-`, `@`, `\t`, or `\r`, spreadsheet engines may interpret the text as an executable dynamic data exchange (DDE) formula or script macro, presenting severe security vulnerabilities.

## Decision
We implemented centralized sanitization in `app/services/export_service.py` via `sanitize_csv_value()`:
1. Every exported cell starting with any character in `('=', '+', '-', '@', '\t', '\r')` is automatically prefixed with a single quote (`'`).
2. Spreadsheet engines treat prefixed values strictly as plain text strings, preventing formula parsing while preserving human readability.

## Consequences
- **Positive**: Complete defense against remote command execution through exported CSV files.
- **Negative**: Text cells intentionally starting with mathematical symbols display with a leading quote in raw text viewers.
