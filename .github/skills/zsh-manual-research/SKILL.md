---
name: zsh-manual-research
description: Use when a task depends on what Zsh itself does, such as investigating a zsh-lint parser gap, false accept, or rule proposal, deciding whether a construct is valid Zsh, or explaining an expansion, option, or builtin. Grounds the answer in the released Zsh manual and native zsh instead of memory or another shell.
---

# Research Zsh behavior from primary sources

The released official Zsh manual is the semantic authority
(`zsh/authority/released-manual` in
`.github/instructions/zsh-scripting.instructions.md`), and released `zsh` is
the syntax authority (`zsh/validation/native-authority`). This skill says how
to reach both and how to record what you found. It adds no rules of its own.

## Find the baseline

1. Read the reviewed release in `lib/zsh-standard-policy.json`
   (`stable_release.version`) and the owning repository's compatibility floor.
2. Run `zsh --version` for the binary you will use as the oracle. If it
   differs from the reviewed release, say so wherever you cite it.

## Look things up in this order

1. **Installed man pages**, which describe the binary you test against:
   `man zshmisc` (grammar, redirection, functions, command execution),
   `man zshexpn` (expansion and globbing), `man zshparam` (parameters and
   subscripts), `man zshoptions`, `man zshbuiltins`, `man zshzle`,
   `man zshcompsys`. Search with `man -P cat zshexpn | grep -n -- 'PATTERN'`;
   `man zshall` holds every page in one file.
2. **The released HTML manual** at
   `https://zsh.sourceforge.io/Doc/Release/`, for the stable link you cite.
   Take the page name and `#anchor` from the page itself; never compose an
   anchor from memory.
3. **Native zsh**, to settle validity: `zsh -f -n FILE`. Judge by stderr, not
   the exit status (`! true` exits 1 with no error), and judge files, not `-c`
   strings. `-n` does not evaluate arithmetic or expand assignment words, so
   some invalid sources pass it and fail only when run. It proves syntax, not
   behavior; behavior needs a runtime test under `zsh -f` in a temporary
   directory.
4. **Zsh source at the release tag** (`Src/parse.c`, `Src/lex.c`,
   `Src/subst.c`, `Doc/Zsh/*.yo`), only when the manual is silent and a
   grammar question needs it. Use the tag matching the reviewed release
   (`zsh-5.9.2` in `https://git.code.sf.net/p/zsh/code`). A vendored or
   development snapshot is not the release.
5. **The zsh-workers archive and `NEWS`/release notes**, for why behavior
   changed and in which release.

These do not ground a Zsh claim: memory of the manual, the Bash manual,
POSIX (except where the Zsh manual defers to it), ShellCheck, what `mvdan/sh`
or another parser accepts, blog posts, and answers on Q&A sites. They may
suggest where to look.

## When sources disagree

- Native zsh decides whether code is valid. The manual decides the wording
  and rationale of a diagnostic.
- If the manual is silent, or native behavior contradicts it, record both:
  the manual section, the `zsh --version` output, and the exact native result.
  Do not paper over the gap with a guess.
- If behavior differs between releases, name the first release with the
  current behavior and check it against the repository's floor.

## Record the evidence

Every conclusion names its manual section as a link,
`https://zsh.sourceforge.io/Doc/Release/<Page>.html#<Section>`, plus the man
page name when that helps a reader offline, for example
`zshmisc(1), Complex Commands`.

In zsh-lint, the citation is checked:

- A rule's doc comment links the manual or Plugin Standard section in its Why
  text (`docs/project/rule-policy.md`, "Manual grounding").
- A parser issue body links the section that defines the construct, and every
  new `gap-`, `ok-` or `invalid-` fixture carries a `# Manual: <url>` line
  (`docs/project/parser-gap-workflow.md`, "Classify" and "Promote to
  fixture"). `internal/manualcite` fails on a missing citation or a page the
  released manual does not have.

For Plugin Standard questions, the canonical source is the
[Zsh Plugin Standard](https://wiki.zshell.dev/community/zsh_plugin_standard);
it does not override the manual on language semantics.
