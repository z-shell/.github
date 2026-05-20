---
name: feedback-agent-files
description: Which agent instruction files are allowed in Z-Shell repos and where
metadata: 
  node_type: memory
  type: feedback
  originSessionId: fe8731b7-1077-4aa3-864d-f92ef1951286
---

Only these agent instruction files are permitted in Z-Shell repos:

- `AGENTS.md` — at repo root
- Files under `.github/` — e.g. `.github/copilot-instructions.md`, `.github/instructions/*.instructions.md`

**Never create** `CLAUDE.md`, `GEMINI.md`, or any other root-level agent file.

**Why:** User's explicit rule. These files were created by mistake during zsh-eza cleanup and had to be removed.

**How to apply:** When working in any Z-Shell repo, do not create `CLAUDE.md` or `GEMINI.md` at the root. If found, remove them. Keep agent context in `AGENTS.md` or `.github/` only.

Also: never use relative paths like `../../CLAUDE.md` in `AGENTS.md` — those are local workspace paths that break on GitHub. Reference external rules via full GitHub URLs (e.g. `https://github.com/z-shell/.github`).
