# 38. Prefer minimal tool attribution and control agent output

- **Status:** PROPOSED
- **Date:** 2026-10-08
- **Deciders:** TBD
- **Supersedes:** None
- **Superseded by:** None

## Context

The former organization rule prohibited bot and AI co-author trailers and treated recognized identities as commit-validation failures. Zi's PR checklist emphasized that permitted co-authors were real humans. That framing could be mistaken for a claim that contributions were produced exclusively by humans.

Automatic tool credits disclose development tooling. A published detection study uses commit attribution, author identities, and configuration files to identify coding-agent activity at scale. GitHub security researchers have demonstrated prompt injection through issue and PR content that agents read, including token exposure and unauthorized execution. Tool disclosure could help attackers select targets or tailor payloads, but these sources do not establish that attribution causes attacks, increases attack rates, or measures how many agents participated. Omitting credits reduces one signal; public configuration and workflows remain other signals.

## Decision

1. Ask contributors to omit automatic tool-credit trailers and generated-with footers as a preference. Attribution alone does not block a contribution.
2. Preserve accurate contributor identities and required license or third-party notices. A missing tool credit does not imply exclusively human authorship. Describe tool use when it is relevant to review, and never fabricate human credit or conceal it through false claims.
3. Keep a firm output rule for agents authoring commits or public project text: omit automatic tool credits, AI co-author and session trailers, and session links. Disable runtime defaults where supported and verify the exact outgoing text, including the final merge message. Local hooks may reinforce this rule without making it a universal contributor gate.
4. Keep commit-format, PR-title, branch-name, and issue-traceability gates. Recognized tool-credit trailers receive advisory warnings. Retain the shared workflow's legacy input name for caller compatibility.
5. Update the shared organization workflow and zi's local copy together. Pinned callers retain their previous behavior until a reviewed pin update; do not claim organization-wide rollout from a change to the shared source alone.

This revision changes only the attribution portions of ADR-0009 and ADR-0013. It does not change signing, decision authority, repository settings, or required review and security controls.

## Consequences

- Contributor guidance states its purpose without suggesting that AI-assisted work is prohibited or exclusively human-authored.
- Managed agents still omit automatic credits, while truthful review context and contributor credit remain available.
- Advisory CI avoids forcing contributors to rewrite history solely to remove a tool marker.
- Instructions and known-signature filters cannot guarantee that every possible credit is absent. Validate managed output and keep approval boundaries; minimal attribution is not an access-control mechanism.
- Pinned callers need a subsequent rollout after the shared workflow revision is published.

## Alternatives considered

- Keep the universal blocking ban: retains a stronger merge gate for a preference whose effect on attack rates is unproven.
- Remove all guidance and controls: permits automatic defaults to publish unnecessary tool and session metadata from managed agents.
- Replace tool credits with human identities: rejected because it would misrepresent contributor provenance.

## References

- [Contribution preference and evidence](../.github/CONTRIBUTING.md#tool-attribution)
- [Organization agent instructions](../AGENTS.md)
- [Detecting AI Coding Agents in Open Source](https://arxiv.org/html/2606.24429v1)
- [GitHub: Safeguarding VS Code against prompt injections](https://github.blog/security/vulnerability-research/safeguarding-vs-code-against-prompt-injections/)
- [GitHub: Creating a commit with multiple authors](https://docs.github.com/en/pull-requests/how-tos/commit-changes/creating-a-commit-with-multiple-authors)
- [Former public-output rule, issue 652](https://github.com/z-shell/.github/issues/652)
