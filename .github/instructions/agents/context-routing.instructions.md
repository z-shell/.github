---
description: "Select authoritative, task-relevant context across Z-Shell repositories"
applyTo: "**"
---

<!-- GENERATED from knowledge/domains/agents/context-routing.md. Do not edit this delivery copy.
Regenerate: python3 automation/knowledge/knowledge-delivery.py
Check: python3 automation/knowledge/knowledge-delivery.py --check -->

# Context routing

Determine the owning repository, requested outcome and affected paths before loading context. Start with its AGENTS.md and instruction manifest. Use [knowledge domains](../../../knowledge/index.md) to find maintained owners, not as a substitute for required instruction selection.

1. Match each manifest surface against the task and repository-relative paths. When both dimensions are declared, both must match. Include read-only review and diagnosis; empty selector dimensions impose no restriction.
2. Read every selected required resource. A link or manifest entry alone does not load its target. Deduplicate byte-identical content while retaining every matching route's provenance.
3. Load optional skills and roles for the requested outcome, then only their relevant supporting references. Keep project internals with the owning project and avoid unrelated repository state.
4. Cache selection by repository, task class, normalized matched paths and relevant content hashes. Reselect when any component changes.

Name exact paths and symbols when recording evidence. For shell work, classify native Zsh, Bash or POSIX sh and the execution profile; establish the repository compatibility floor before applying language guidance. Go parser work still requires Zsh authority for the language behavior being analyzed.

For multi-file or cross-repository changes, agree on the implementation boundary before mutations. A selected role, skill or domain does not expand authorization. Report missing owners, conflicting rules and unverified runtime loading explicitly.
