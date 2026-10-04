# Model z-shell knowledge domains

Use this procedure when changing knowledge boundaries, terminology or ownership. Reading existing terminology alone does not require redesigning the model.

Inspect the relevant domain indexes, glossary, current source and accepted decisions. Separate a domain's subject from its audience, authority, editable owner and delivered formats. A directory label alone does not establish an independent domain.

Resolve ambiguous terms against concrete examples. Check claims against the owning source. Ask for clarification when competing meanings change scope or behavior; retain settled terms when the meaning is already clear. Record resolved, domain-specific terms in the smallest existing glossary. Keep definitions concise and leave procedures and implementation decisions in their own owners.

For z-shell, test boundaries with cases such as:

- A portable plugin follows Zsh semantics and the plugin standard; manager-specific integration is selected separately.
- A parser adapter belongs to tooling and must remain compatible with the owning project's tested revision; the official Zsh manual owns language validity.
- An organization runbook defines a repeatable procedure, while a skill supplies task discovery and routes to that procedure.
- A wiki page can present centrally maintained knowledge; its public presentation path does not establish the editable source owner.

Document cross-domain relationships in the existing domain indexes. Reuse a maintained owner and link it from other domains rather than restating its contract. Add a glossary only when there are resolved concepts to capture, and a new domain only when the inventory demonstrates a distinct responsibility.

Use the existing z-shell ADR procedure and decisions/ numbering for meaningful ownership or architecture choices. New decisions remain proposed until maintainer acceptance; upstream example layouts do not replace organization policy.

Adapted from [Matt Pocock's domain-modeling skill](https://github.com/mattpocock/skills/tree/main/skills/engineering/domain-modeling), checked 2026-10-04, SKILL.md blob a4438c6879c517d1a08e2b5fbca049b632688dfe. Its active terminology checks, concrete scenarios and selective glossary capture inform this procedure. z-shell retains its domain indexes, canonical-source delivery and ADR contracts. Refresh the reference when its upstream model changes or these ownership boundaries change.
