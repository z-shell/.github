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
- GitHub issues and pull requests remain authoritative for active work, and the
  wiki remains authoritative for durable long-form documentation. Project 28
  and any Linear mirror are views, not independent authorities. Record
  tool-derived findings in the owning GitHub record, not only in local memory.

## Copilot hosted review

Check the current [GitHub MCP configuration documentation](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/configure-mcp-servers)
before configuring a repository. These hosted constraints do not describe every
interactive MCP client:

| Capability            | Hosted requirement                                                                                       |
| --------------------- | -------------------------------------------------------------------------------------------------------- |
| Configuration         | Repository Settings > Copilot > MCP servers, shared with cloud agent                                     |
| Defaults              | GitHub and Playwright servers are enabled by default; verify the repository's actual state               |
| Protocol              | Tools only; resources and prompts are unsupported                                                        |
| Remote authentication | Remote OAuth servers are unsupported                                                                     |
| Review tools          | `tools/list` must return `annotations.readOnlyHint: true`; missing or false annotations exclude the tool |
| Credentials           | Reference Agents secrets or variables prefixed `COPILOT_MCP_`; never commit values                       |

Use explicit read-tool allowlists and credentials restricted to the required
read access. An annotation is not an access-control boundary. Configured tools
can run without per-call approval; inspect the shared cloud-agent exposure too.
Configuration and credential changes require separate maintainer authorization.
A committed configuration draft does not prove that hosted settings are active.

Select the smallest useful profile from the repository's actual components:

- **`github`:** baseline for linked issue acceptance criteria, relevant PRs and
  CI evidence. Read canonical organization policy and wiki contracts through
  existing accessible sources. Do not broaden repository access implicitly.
- **`github-docs`:** add documentation lookup only for framework, API, or
  platform changes that need it, such as wiki Docusaurus or Cloudflare changes.
  Prefer official version-matched documentation; Context7 or Cloudflare's
  documentation server is optional. Check actual tools and annotations before
  selecting either. Operational Cloudflare access is outside this profile.
- **Linear:** optional addition only when a linked requirement is unavailable
  in GitHub. Evaluate a restricted read-only API-key configuration if supported
  by the current server; interactive OAuth availability proves no hosted
  compatibility. Do not mirror all tracker context into every review.

Playwright is relevant to browser behavior and previews only when suitable
tools are available to that review. Neither browser checks nor a third-party
documentation service is required for repositories that do not need them.
See [the health evidence procedure](../../runbooks/org-review.md#mcp-review-context)
for configuration, discovery, and invocation verification.

## Interactive runtime integrations

The following integrations describe interactive clients with the stated
capabilities. Discover the actual transport, authentication, and tools; do not
copy OAuth configurations into hosted review settings.

### Context7

- **Availability:** optional; use only when present.
- **Purpose:** current docs and code examples for libraries and frameworks
  (Docusaurus, React, wrangler, etc.).
- **When to use:** before assuming API or config behavior; version migrations;
  setup and CLI usage questions.
- **When NOT to use:** business-logic debugging, refactoring, or general
  programming concepts.

### Cloudflare (OAuth)

- **Availability:** optional; use only when present.
- **Purpose:** Pages, Workers, R2, and observability for the wiki, which
  continuously deploys from `main`.
- **When to use:** verify Pages deployments, inspect logs, R2 work (see the
  `wiki-r2-proxy` spec), and debug Pages Functions.
- **When NOT to use:** no production deploys or binding changes without
  confirmation.
- **Auth required:** yes (OAuth).

### Greptile (OAuth)

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
