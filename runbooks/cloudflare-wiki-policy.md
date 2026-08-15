# Runbook - Cloudflare Wiki Policy Inspection and Rollback

Use this runbook to inspect the Cloudflare controls that affect the public
Z-Shell wiki, compare deployed behavior with repository policy, and recover from
a bad Cloudflare Pages production deployment.

**Owner:** [@ss-o](https://github.com/ss-o)

**Hard rule:** inspection is read-only by default. Do not change a Cloudflare
setting, enable a dataset or retention feature, create a logging job, or roll a
deployment backward or forward without explicit maintainer approval for the
exact action and target.

## Scope

This runbook covers:

- Cloudflare Pages production deployments for `wiki.zshell.dev`;
- AI Crawl Control visibility into crawler activity and `robots.txt`;
- Web Analytics, advanced HTTP traffic analytics, and available request logs;
- the repository-owned crawler and `Content-Signal` policy; and
- rollback to, and restoration from, a known-good Pages deployment.

It does not authorize a policy change, a new logging pipeline, or expanded data
collection. Make repository policy changes in
[`z-shell/wiki`](https://github.com/z-shell/wiki) through its normal review and
release process.

## Security and privacy boundary

Keep public evidence limited to public repository references, commit SHAs,
aggregate counts, public paths, HTTP status codes, public response headers, and
sanitized conclusions.

Do not put any of the following in a public issue, pull request, or runbook:

- account, zone, project, or deployment identifiers;
- tokens, secret values, private settings, or internal hostnames;
- screenshots that expose account or member details;
- client IP addresses, cookies, request headers, referrers, or raw user-agent
  strings from general traffic;
- response headers other than the public `Content-Type`, `Cache-Control`, and
  `Content-Signal` fields explicitly used by this runbook; or
- query strings, prompts, search text, or other personal data.

Keep restricted evidence in the approved private incident or operations system.
If sanitization would remove the evidence needed to support a conclusion, keep
the conclusion private.

## Capability states

Record every Cloudflare surface with one of these states. Never infer a feature,
plan, retention period, or permission from public documentation alone.

| State            | Meaning                                                        |
| ---------------- | -------------------------------------------------------------- |
| `Available`      | The operator opened the surface and read the required evidence |
| `Unavailable`    | The account or plan does not expose the required capability    |
| `Not authorized` | The capability exists, but the operator cannot read it         |
| `Not tested`     | The capability was not attempted during this inspection        |

Use `Not tested`, with a reason, when the result is ambiguous.

## Start an inspection record

Create or update the owning public issue before inspection. Use a private
incident record instead when the investigation may contain sensitive evidence.
Do not replace an existing issue or incident owner with a separate local note.

Copy this public-safe template:

```text
Inspection date and time (UTC):
Operator:
Owner:
Reason:
Related issue, pull request, or incident:
Wiki production commit:
Public verification status: Pass | Fail | Not tested

| Surface | State | Observed retention or window | Available fields or metrics | Public-safe conclusion |
| --- | --- | --- | --- | --- |
| Pages deployments | Not tested | Not tested | Not tested | Not tested |
| AI Crawl Control Directives | Not tested | Not tested | Not tested | Not tested |
| AI Crawl Control Metrics | Not tested | Not tested | Not tested | Not tested |
| Web Analytics | Not tested | Not tested | Not tested | Not tested |
| Advanced HTTP traffic analytics | Not tested | Not tested | Not tested | Not tested |
| Log Explorer | Not tested | Not tested | Not tested | Not tested |
| Logpull | Not tested | Not tested | Not tested | Not tested |
| Logpush | Not tested | Not tested | Not tested | Not tested |
| Pages Functions logs | Not tested | Not stored | Live Function events | Not tested |

Policy comparison:
Rollback candidate:
Rollback approval: Not requested | Pending | Approved | Rejected
Rollback result: Not run | Pass | Fail
Forward-restoration result: Not run | Pass | Fail
Follow-up owner and next step:
```

Do not replace `Not tested` with a provider-documented maximum or with a result
from another account.

## Establish the repository baseline

Record the exact wiki commit associated with the current production deployment.
Inspect policy at that commit, not from an unrelated working branch.

The repository sources of truth are:

| Source                                                                                             | What to compare                                               |
| -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| [`content-policy.json`](https://github.com/z-shell/wiki/blob/main/content-policy.json)             | Expected `Content-Signal` value                               |
| [`scripts/llms/config.mjs`](https://github.com/z-shell/wiki/blob/main/scripts/llms/config.mjs)     | Crawler matrix and generated `robots.txt` inputs              |
| [`static/_headers`](https://github.com/z-shell/wiki/blob/main/static/_headers)                     | Response-header rules for public and machine-readable paths   |
| [`functions/[[path]].ts`](https://github.com/z-shell/wiki/blob/main/functions/%5B%5Bpath%5D%5D.ts) | Header behavior for Pages Functions and R2 fallback responses |

Do not copy these values into a second policy document. If the production
deployment points at an older commit, use the files from that exact commit for
the comparison and record the drift from the current `main` branch.

## Verify public behavior first

Public verification does not require Cloudflare account access. Check at least:

- `/`;
- `/robots.txt`;
- `/llms.txt`;
- `/llms-full.txt`;
- `/ai/v1/manifest.json`; and
- one canonical HTML page and its manifest-declared Markdown artifact.

For each response, record only the status, `Content-Type`, `Cache-Control`, and
`Content-Signal` headers. Count raw `Content-Signal` header lines before any HTTP
client combines duplicates. The header must appear exactly once and match the
value from `content-policy.json` at the production commit.

The following Zsh command prints only the public-safe headers:

```zsh
base=https://wiki.zshell.dev
for endpoint in / /robots.txt /llms.txt /llms-full.txt /ai/v1/manifest.json; do
  print -r -- "== ${endpoint} =="
  curl --silent --show-error --dump-header - --output /dev/null \
    "${base}${endpoint}" |
    grep -Ei '^(HTTP/|content-type:|cache-control:|content-signal:)'
done
```

Do not publish the unfiltered response headers. Dynamic provider headers are not
needed for this comparison.

At the exact production commit, run the wiki repository's documented clean
validation and production build. Compare the deployed `/robots.txt` body
byte-for-byte with the generated build artifact. Also confirm:

1. the manifest is valid JSON;
2. its declared machine-readable artifacts return the declared media types;
3. the public crawler directives match the generated crawler matrix; and
4. the effective `Content-Signal` is neither absent nor duplicated.

A public mismatch is actionable even when every account-only capability is
`Unavailable`, `Not authorized`, or `Not tested`.

## Inspect Cloudflare without changing state

Use a read-only account role. Cloudflare provides a domain-scoped **AI Crawl
Control Read Only** role for that product; access to Pages, analytics, or logs
requires its own appropriate read permission. If the operator cannot open a
surface, record `Not authorized` rather than requesting broader access during
the inspection.

### Inspect Pages deployments

1. Open **Workers & Pages**, select the wiki Pages project, then open
   **Deployments**.
2. Record the current production deployment's status, creation time, source
   branch, and Git commit in the restricted record.
3. In public evidence, record only the commit SHA and a public GitHub workflow,
   pull request, or commit link.
4. Review build logs only for deployment and build failures. Do not treat them
   as evidence of ordinary HTTP requests.
5. Do not open a rollback confirmation while performing a routine inspection.

### Inspect AI Crawl Control

1. Select the wiki domain, then open **AI Crawl Control**.
2. On **Overview**, record whether managed `robots.txt` is reported as enabled
   or disabled. This is an observation, not permission to toggle it.
3. On **Directives** (called **Robots.txt** in some role documentation), record
   file availability, HTTP status, Content Signals detection, and aggregate
   violations for the selected time window.
4. On **Metrics**, filter to the production hostname and then to each discovery
   path. Record aggregate requests, response status groups, crawler or operator,
   and the selected date range.
5. Record whether hostname and path filters are available. If the current
   product surface cannot distinguish the required paths, mark that requirement
   `Unavailable`.

Do not select crawler **Allow** or **Block** actions during inspection. A
`robots.txt` violation is calculated against the current directives and may
classify older requests differently after a policy change; preserve the
selected time window and policy commit with the evidence.

### Inspect Web Analytics

Open Web Analytics for the wiki and record whether the path filter and required
date range are available.

Web Analytics is client-side beacon data. It can support HTML page-view
comparisons, but it is not authoritative evidence that raw artifacts such as
`robots.txt`, `llms.txt`, or `llms-full.txt` were requested. An absent Web
Analytics row for one of those paths is not evidence of no requests.

For documentation reference only, Cloudflare currently states that Web
Analytics data is accessible for six months, with unsampled beacon data retained
for seven days before aggregation to approximately 10%. These values are not
evidence of this account's effective window or data granularity. Record what the
Cloudflare UI actually shows during the inspection, or use the appropriate
capability state when it cannot be observed. Recheck the provider documentation
before interpreting the result.

If server-side path evidence is required, check advanced HTTP traffic analytics
or the logging surfaces below. Record unavailable plan features as
`Unavailable`.

### Inspect request logging

Routine release verification should use public responses, the production commit,
and deployment evidence. Do not enable request logging solely to prove a
successful release.

If incident diagnosis requires historical request evidence, inspect existing
capabilities in this order:

1. Log Explorer with an already-enabled `http_requests` dataset;
2. Logpull with retention already enabled; or
3. an existing Logpush destination and its documented retention.

Enabling a dataset or retention flag and creating or changing a Logpush job are
state changes. They may also incur cost. Stop and obtain explicit approval
before doing any of them.

When an existing HTTP request dataset is available, select only the minimum
fields needed:

| Need                                            | Preferred field                              |
| ----------------------------------------------- | -------------------------------------------- |
| Event time                                      | `EdgeStartTimestamp`                         |
| Public hostname                                 | `ClientRequestHost`                          |
| Path without query text                         | `ClientRequestPath`                          |
| Request method                                  | `ClientRequestMethod`                        |
| Response status                                 | `EdgeResponseStatus`                         |
| Response media type, when needed                | `EdgeResponseContentType`                    |
| Provider crawler classification, when available | `VerifiedBotCategory` or documented bot tags |
| Restricted correlation during an incident       | `RayID`                                      |

Do not select `ClientIP`, `ClientRequestURI`, referrer, cookies, custom request
headers, or custom response headers for this workflow. Prefer aggregate crawler
counts. If crawler classification is unavailable and a raw user agent is
essential, keep it restricted and do not publish general-traffic values.

Record the observed retention and these provider constraints:

- HTTP request logs are not retained for Logpull by default. When retention is
  already enabled, Cloudflare documents a query window of at least three and up
  to seven days.
- Logpush does not store or backfill logs. Destination retention applies, and
  logs produced while a job is disabled or failing are lost.
- Log Explorer begins ingesting when a dataset is enabled and has no history
  from before enablement. Record the configured retention shown for the account.
- Pages Functions logs are live streams and are not stored. They are Function
  execution evidence, not a historical zone-request log.

If none of these surfaces can provide path-level request evidence, record that
logging is `Unavailable`, `Not authorized`, or `Not tested`. Do not infer
requests from page views.

## Decide whether rollback is appropriate

Prefer a forward repository fix when production is stable enough to wait for the
normal reviewed deployment path. Consider rollback only when a specific
production deployment introduced material breakage and a known-good production
deployment can restore service or policy safely.

Complete every decision point:

- [ ] The failure is reproduced against the public production hostname.
- [ ] Repository policy and Cloudflare delivery behavior have been compared.
- [ ] The suspected change is tied to the current production deployment rather
      than an unrelated Cloudflare setting.
- [ ] The rollback target is a successful **production** deployment. Preview and
      failed deployments are not valid targets.
- [ ] The target commit passed the required wiki checks and has known-good
      public evidence.
- [ ] The target's crawler, header, and machine-readable artifact behavior is
      understood. Any policy regression is explicitly accepted.
- [ ] The current deployment is recorded as the preferred forward-restoration
      target.
- [ ] A verification owner and communication channel are active.
- [ ] Explicit maintainer approval names the rollback target and restoration
      plan.

If any item is incomplete, stop. Do not use a nearby deployment as a guess.

## Select and record a known-good deployment

Cloudflare permits rollback only to successfully built production deployments.
A preview deployment is not eligible. Record these facts before requesting
approval:

| Evidence           | Required value                                                                         |
| ------------------ | -------------------------------------------------------------------------------------- |
| Current production | Commit SHA, deployment time, public verification result                                |
| Rollback target    | Commit SHA, successful production status, deployment time                              |
| Known-good basis   | Passing checks and prior public or incident evidence                                   |
| Policy delta       | Changes to `robots.txt`, `Content-Signal`, headers, Functions, and generated artifacts |
| Restoration target | Newer successful production commit to restore after mitigation                         |
| Verification owner | Maintainer responsible for immediate post-change checks                                |

Keep provider deployment identifiers and preview hostnames in the restricted
record. A public approval request can identify targets by public commit SHA.

## Obtain explicit approval

Approval must identify:

1. the current production commit;
2. the exact rollback target commit;
3. the reason rollback is safer than a forward fix;
4. the expected policy and artifact regression, if any;
5. the exact forward-restoration target or restoration criteria;
6. the operator and verification owner; and
7. the maintenance or incident window.

A general request to "fix production" is not rollback approval. One approval may
cover rollback and forward restoration only when it names both exact actions and
targets. Otherwise, obtain a second approval before restoration.

## Perform the approved rollback

1. Reconfirm the approval and both target commits immediately before acting.
2. Open the wiki Pages project's **Deployments** page.
3. In **All deployments**, locate the approved successful production
   deployment.
4. Open its actions menu and select **Rollback to this deployment**.
5. In the confirmation window, recheck the production status, commit, and
   deployment time. Cancel if any value differs from the approved record.
6. Confirm once. Cloudflare documents the production change as immediate.
7. Record the action time privately and begin public verification immediately.

Do not change build settings, branch controls, AI crawler actions, managed
`robots.txt`, analytics, or logging configuration as part of the rollback.

## Verify the rollback

Repeat the public behavior checks and compare them with the target commit's
generated output.

- [ ] The homepage and one canonical content page return the expected status.
- [ ] `/robots.txt` matches the target build byte-for-byte.
- [ ] `/llms.txt`, `/llms-full.txt`, and `/ai/v1/manifest.json` have the expected
      status and media type for the target.
- [ ] Every checked response has exactly one `Content-Signal`, matching the
      target commit.
- [ ] No checked path has an unexpected redirect, error, or stale policy.
- [ ] Available aggregate analytics or logs show no new error pattern.
- [ ] The public issue or incident records the result without restricted data.

If verification fails, stop further changes and use the approved restoration
path. Do not chain rollbacks through unreviewed deployments.

## Restore forward

Cloudflare allows a project that has rolled back to select a newer successful
production deployment as another rollback target. Restore by either selecting
the approved newer deployment or by shipping a reviewed fix through the wiki's
normal release path.

1. Confirm the restoration action is covered by approval.
2. Recheck that the restoration target is a successful production deployment.
3. Select **Rollback to this deployment** for that newer target, or wait for the
   approved forward-fix deployment.
4. Repeat the full public verification checklist.
5. Confirm the Pages production commit matches the intended repository state.
6. Close any temporary production-versus-`main` drift in the owning issue.
7. Record the incident result and any follow-up owner.

Do not declare recovery complete while the public policy differs from the
intended repository policy without an explicit, time-bounded exception.

## Exercise and review the runbook

Run a read-only exercise after a material wiki delivery or Cloudflare product
change and before relying on this procedure for an incident:

- [ ] Complete the capability matrix without changing state.
- [ ] Verify all public endpoints and compare policy at the production commit.
- [ ] Identify a successful production deployment that could be a known-good
      target without opening its rollback confirmation.
- [ ] Confirm where restricted deployment evidence and public evidence belong.
- [ ] Review the approval request fields with the maintainer.
- [ ] Mark rollback execution and forward restoration `Not tested` unless an
      explicitly approved maintenance exercise performed both actions.

Record each exercise:

```text
Runbook commit:
Exercise date (UTC):
Operator:
Read-only inspection: Pass | Fail | Not tested
Public verification: Pass | Fail | Not tested
Rollback target selection: Pass | Fail | Not tested
Rollback execution: Pass | Fail | Not tested
Forward restoration: Pass | Fail | Not tested
Observed UI or retention drift:
Follow-up issue and owner:
```

### Initial implementation exercise

| Check                         | Status               | Evidence                                                                                         |
| ----------------------------- | -------------------- | ------------------------------------------------------------------------------------------------ |
| Public header procedure       | `Pass` on 2026-08-14 | All five listed paths returned `200`, the expected media type, and one matching `Content-Signal` |
| Manifest canonical pair       | `Pass` on 2026-08-14 | One declared HTML URL and its Markdown URL returned the expected public response                 |
| Public `robots.txt`           | `Pass` on 2026-08-14 | The deployed crawler groups matched the repository crawler matrix                                |
| Public manifest shape         | `Pass` on 2026-08-14 | The deployed JSON contained document and artifact arrays                                         |
| Repository source links       | `Pass` on 2026-08-14 | All four policy-source links resolved                                                            |
| Cloudflare account inspection | `Not tested`         | No Cloudflare account connector was available to the implementation session                      |
| Rollback and restoration      | `Not tested`         | No production mutation was requested or approved                                                 |

Live account inspection, rollback execution, and forward restoration remain
`Not tested` until a maintainer-authorized operator records an exercise.

## Stop conditions

Stop and escalate to the owner when:

- the production deployment cannot be mapped to a public commit;
- repository policy, generated output, and deployed output disagree in more
  than one unexplained way;
- the proposed target is a preview, failed, or unverified deployment;
- the current deployment was not recorded for restoration;
- approval is absent, ambiguous, expired, or names a different target;
- verification requires collecting query text, prompts, client IP addresses, or
  other personal data; or
- a Cloudflare UI or product change makes a step uncertain.

Record uncertainty as `Not tested`; do not improvise a production mutation.

## References

- [Cloudflare Pages rollbacks](https://developers.cloudflare.com/pages/configuration/rollbacks/)
- [Cloudflare AI Crawl Control Directives](https://developers.cloudflare.com/ai-crawl-control/features/track-robots-txt/)
- [Cloudflare AI traffic analysis](https://developers.cloudflare.com/ai-crawl-control/features/analyze-ai-traffic/)
- [Cloudflare AI Crawl Control Read Only role](https://developers.cloudflare.com/changelog/post/2026-01-13-ai-crawl-control-read-only-role/)
- [Cloudflare Web Analytics FAQs](https://developers.cloudflare.com/web-analytics/faq/)
- [Cloudflare Pages Functions logging](https://developers.cloudflare.com/pages/functions/debugging-and-logging/)
- [Cloudflare HTTP request log fields](https://developers.cloudflare.com/logs/logpush/logpush-job/datasets/zone/http_requests/)
- [Cloudflare Logpull retention](https://developers.cloudflare.com/logs/logpull/enabling-log-retention/)
- [Cloudflare Logpull data window](https://developers.cloudflare.com/logs/logpull/understanding-the-basics/)
- [Cloudflare Logpush](https://developers.cloudflare.com/logs/logpush/)
- [Cloudflare Log Explorer FAQ](https://developers.cloudflare.com/log-explorer/faq/)
- [Wiki machine-readable documentation implementation issue](https://github.com/z-shell/wiki/issues/795)
- [Cloudflare wiki inspection and rollback issue](https://github.com/z-shell/.github/issues/459)
