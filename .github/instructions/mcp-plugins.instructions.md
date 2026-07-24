---
description: "Capability-conditional guidance for optional tool integrations across Z-Shell repositories; discover available tools before use and fall back to official documentation or local search."
applyTo: "**"
---

# Optional Tool Integrations

Guidance for optional MCP servers and agent toolkits. Availability varies by
runtime: discover available tools first, use a named tool only when present,
and otherwise consult official documentation or search the local repository.

## General rules

- Discover the current runtime's capabilities before selecting an integration.
- Use Context7 for library, framework, or API documentation only when it is
  available; otherwise use official documentation or local search.
- Treat every available OAuth-gated integration (including Cloudflare and
  Greptile) as touching a **live external service**. Read-only by default;
  confirm with the user before any write, deploy, secret change, or other
  outward-facing action.
- GitHub, the wiki, and the Z-Shell Tracker remain the source of truth. Record
  tool-derived findings in PRs and issues, not only in local agent memory.

## Context7 (no auth)

- **Availability:** optional; use only when present.
- **Purpose:** current docs and code examples for libraries and frameworks
  (Docusaurus, React, wrangler, etc.).
- **When to use:** before assuming API or config behavior; version migrations;
  setup and CLI usage questions.
- **When NOT to use:** business-logic debugging, refactoring, or general
  programming concepts.

## Cloudflare (OAuth)

- **Availability:** optional; use only when present.
- **Purpose:** Pages, Workers, R2, and observability for the wiki, which
  continuously deploys from `main`.
- **When to use:** verify Pages deployments, inspect logs, R2 work (see the
  `wiki-r2-proxy` spec), and debug Pages Functions.
- **When NOT to use:** no production deploys or binding changes without
  confirmation.
- **Auth required:** yes (OAuth).

## Greptile (OAuth)

- **Availability:** optional; use only when present.
- **Purpose:** semantic code search across multiple repositories.
- **When to use:** cross-repo reference scans before moves or renames; locating
  patterns that span repositories.
- **When NOT to use:** single-file lookups where local grep or Read is faster.
- **Auth required:** yes (OAuth). Read-only.

## CLI Agent toolkits

- Use each toolkit only when the current runtime exposes it. Otherwise perform
  the equivalent review with repository files and official documentation.
- **pr-review-toolkit:** reviewer, silent-failure, type-design, test, and
  comment subagents. Run on a diff before requesting human review.
- **hookify:** generate CLI hooks/heuristics from recurring conversation mistakes.
- **security-guidance:** security review of pending changes before merge.
