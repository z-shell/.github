---
description: "When and how to use the project MCP plugins (Context7, Cloudflare, Greptile) and Claude Code toolkits (pr-review-toolkit, hookify, security-guidance) across the Z-Shell workspace."
applyTo: "**"
---

# Project MCP Plugins

Guidance for the MCP servers and Claude Code plugins enabled in the Z-Shell
maintainer workspace. Prefer these over guesswork or generic web search.

## General rules

- Prefer Context7 over web search for any library, framework, or API documentation.
- Treat every OAuth-gated plugin (Cloudflare, Greptile) as touching a
  **live external service**. Read-only by default; confirm with the user before
  any write, deploy, secret change, or other outward-facing action.
- GitHub, the wiki, and the Z-Shell Tracker remain the source of truth. Record
  plugin-derived findings in PRs and issues, not only in local agent memory.

## Context7 (no auth)

- **Purpose:** current docs and code examples for libraries and frameworks
  (Docusaurus, React, wrangler, etc.).
- **When to use:** before assuming API or config behavior; version migrations;
  setup and CLI usage questions.
- **When NOT to use:** business-logic debugging, refactoring, or general
  programming concepts.

## Cloudflare (OAuth)

- **Purpose:** Pages, Workers, R2, and observability for the wiki, which
  continuously deploys from `main`.
- **When to use:** verify Pages deployments, inspect logs, R2 work (see the
  `wiki-r2-proxy` spec), and debug Pages Functions.
- **When NOT to use:** no production deploys or binding changes without
  confirmation.
- **Auth required:** yes (OAuth).

## Greptile (OAuth)

- **Purpose:** semantic code search across the **multi-repo** workspace.
- **When to use:** cross-repo reference scans before moves or renames; locating
  patterns that span repositories.
- **When NOT to use:** single-file lookups where local grep or Read is faster.
- **Auth required:** yes (OAuth). Read-only.

## Claude Code toolkits

- **pr-review-toolkit:** reviewer, silent-failure, type-design, test, and
  comment subagents. Run on a diff before requesting human review.
- **hookify:** generate Claude Code hooks from recurring conversation mistakes.
- **security-guidance:** security review of pending changes before merge.
