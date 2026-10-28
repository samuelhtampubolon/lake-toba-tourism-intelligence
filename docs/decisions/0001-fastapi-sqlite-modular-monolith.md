# ADR 0001: FastAPI Modular Monolith with SQLite Persistence

## Status
Accepted

## Context
Lake Toba Tourism Intelligence is designed for local-first decision support by regional operators and government analysts. It must execute reliably within a 2 GB RAM / 2 CPU core resource envelope without requiring complex multi-container Docker orchestration, Kubernetes clusters, cloud subscriptions, or external network connections.

## Decision
We chose a **FastAPI Modular Monolith** with server-rendered Jinja2 templates and local disk **SQLite 3** persistence utilizing:
1. `PRAGMA foreign_keys = ON;` to enforce relational integrity.
2. `PRAGMA journal_mode = WAL;` (Write-Ahead Logging) to allow concurrent non-blocking reads.
3. Native `sqlite3.Connection.backup()` for atomic, hot snapshot backups.

## Consequences
- **Positive**: Single process footprint (&lt;180MB RAM), zero operational overhead, instantaneous zero-config startup, and 100% offline functionality.
- **Negative**: Concurrency is serialized on writes; unsuitable for multi-host distributed clusters. If horizontal scale across multiple independent writer nodes is required in future releases, a migration path to PostgreSQL is documented in `docs/architecture.md`.
