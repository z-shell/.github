# Imported knowledge requiring decisions or refresh

Checked against the local organization repository on 2026-10-04. Importing a document preserves its existing requirements; it does not certify legal applicability, current membership or an example's operational suitability.

| Source | Verified gap | Remaining action |
| --- | --- | --- |
| [Charter](charter.md), [project governance](project-governance.md), [maintainers](maintainers.md), [steering committee](steering-committee.md) | These contain voting, role and membership declarations; this migration preserved the text without verifying current governance operation or affiliations | Maintainer review is needed before treating the imported roster and governance procedure as confirmed current |
| [Commit action guide](../ci/commit-action.md) and [rclone action guide](../ci/rclone-action.md) | Existing examples use actions/checkout@v3 and mutable/tag action references, unlike the current full-SHA workflow contract | Refresh examples against executable action inputs, permissions and current workflow conventions in a separate scoped accuracy pass |

These are retained, useful documents with unresolved accuracy questions, not deletion candidates. Their complete native consumers remain generated from the listed sources. The orphaned workflow-templates/project-tracker.properties.json was separately removed with explicit maintainer approval: it had no matching workflow or repository references.
