# Zi

Select this domain for the plugin manager or Zi-specific annex behavior. Portable plugin requirements belong to [plugins](../plugins/index.md).

| Task | Authoritative context |
| --- | --- |
| Understand the canonical manager decision | [ADR-0002](../../../decisions/0002-zi-as-canonical-plugin-manager.md) |
| Install or update Zi | [`zi-install` skill](https://github.com/z-shell/agent-skills/blob/main/plugins/z-shell/skills/zi-install/SKILL.md) in `z-shell/agent-skills` and the [Zi repository](https://github.com/z-shell/zi) |
| Understand promotion and release boundaries | [Branch model](../../../decisions/0019-trunk-on-main-default.md) and [promotion authorization](../../../decisions/0028-zi-promotion-is-release-authorization.md) |

Read the owning Zi or annex checkout's instructions and current implementation before assuming an API, installation location or compatibility floor. End-user guides belong in the [wiki](https://wiki.zshell.dev/).

For native packages, historical records, implementation and supporting files in this domain, use [repository resources](repository-resources.md). Each file has an imported source or retained-owner reference in the checked repository inventory.
