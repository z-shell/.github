# Plan coordinated knowledge migrations

Use this procedure when a migration crosses repositories, changes source ownership or cannot be verified in one local batch. Start with the destination, approved scope, current owners, affected consumers and explicit unknowns. Load [domain modeling](domain-modeling.md); use [research](knowledge-research.md) for missing facts and [decision clarification](decision-clarification.md) for consequential choices.

Separate unresolved decisions from implementation work. Keep a compact parent record linking the detailed evidence or task that owns each resolution. State which prerequisites actually block a batch and what is outside the requested destination.

Once decisions are settled, synthesize a migration contract: problem, chosen source and consumer model, essential rules, acceptance evidence, exclusions and rollout order. Capture already agreed decisions rather than repeating an interview.

Plan complete, independently verifiable slices. For an ownership rename that must remain compatible, add the new source and delivery first, migrate consumers in bounded batches, and retire old authoring paths only after coverage passes. Keep source publication, downstream pins, native discovery and final removal as distinct dependencies.

Route coordinated issues and dependencies through [the sub-issue procedure](../governance/sub-issues.md). Use the relevant project issue or workspace note for complex cases under the current authorization. A local plan does not itself authorize tracker writes, branch changes or publication.

Finish when every in-scope artifact has a disposition, consumer and check, or an explicitly tracked unresolved prerequisite. The map is navigation; each decision and implementation contract has one detailed owner.

Adapted from [wayfinder](https://github.com/mattpocock/skills/tree/main/skills/engineering/wayfinder), [to-spec](https://github.com/mattpocock/skills/tree/main/skills/engineering/to-spec) and [to-tickets](https://github.com/mattpocock/skills/tree/main/skills/engineering/to-tickets), checked 2026-10-04. z-shell retains its tracker, task ownership and authorization workflow, with no imported labels or automatic issue closure.
