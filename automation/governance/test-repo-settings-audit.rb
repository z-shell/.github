#!/usr/bin/env ruby
# frozen_string_literal: true

require "json"
require "stringio"
require "tmpdir"
require "yaml"

require_relative "repo-settings-audit"

class RepoSettingsAuditTest
  FIXTURES = File.expand_path("fixtures/repo-settings", __dir__)
  CLASSES_FILE = File.expand_path("../../knowledge/domains/governance/data/repository-classes.yml", __dir__)

  def assert_equal(expected, actual)
    raise "expected #{expected.inspect}, got #{actual.inspect}" unless expected == actual
  end

  def assert(value, message = "expected truthy value")
    raise message unless value
  end

  def refute(value, message = "expected falsey value")
    raise message if value
  end

  # --- ClassResolver ---------------------------------------------------

  def test_class_resolver_returns_explicit_class_for_a_listed_repo
    resolver = RepoSettingsAudit::ClassResolver.load(CLASSES_FILE)

    assert_equal(1, resolver.class_for("z-shell/wiki"))
    assert_equal(2, resolver.class_for("z-shell/zsh-lint"))
    assert_equal(4, resolver.class_for("z-shell/.github"))
  end

  def test_class_resolver_falls_back_to_default_class_for_an_unlisted_repo
    resolver = RepoSettingsAudit::ClassResolver.load(CLASSES_FILE)

    assert_equal(3, resolver.class_for("z-shell/some-new-plugin"))
  end

  def test_class_resolver_reports_source_explicit_vs_default
    resolver = RepoSettingsAudit::ClassResolver.load(CLASSES_FILE)

    assert_equal("explicit", resolver.source_for("z-shell/wiki"))
    assert_equal("default", resolver.source_for("z-shell/some-new-plugin"))
  end

  def test_class_resolver_returns_named_settings_overrides
    resolver = RepoSettingsAudit::ClassResolver.load(CLASSES_FILE)

    assert_equal({ "linear_history" => "-" }, resolver.settings_overrides_for("z-shell/zi"))
    assert_equal({}, resolver.settings_overrides_for("z-shell/wiki"))
  end

  # --- Baseline ----------------------------------------------------------

  def test_baseline_disposition_matches_the_adr_0013_table
    assert_equal("R", RepoSettingsAudit::Baseline.disposition(1, "required_status_checks"))
    assert_equal("R", RepoSettingsAudit::Baseline.disposition(3, "required_status_checks"))
    assert_equal("S", RepoSettingsAudit::Baseline.disposition(1, "linear_history"))
    assert_equal("S", RepoSettingsAudit::Baseline.disposition(2, "linear_history"))
    assert_equal("R", RepoSettingsAudit::Baseline.disposition(4, "copilot_code_review"))
    assert_equal("S", RepoSettingsAudit::Baseline.disposition(3, "copilot_code_review"))
    (1..4).each { |klass| assert_equal("R", RepoSettingsAudit::Baseline.disposition(klass, "review_thread_resolution")) }
  end

  def test_baseline_applies_a_named_repository_override
    disposition = RepoSettingsAudit::Baseline.disposition(
      3, "linear_history", overrides: { "linear_history" => "-" }
    )
    assert_equal("-", disposition)
  end

  def test_baseline_rejects_an_unknown_class
    error = begin
      RepoSettingsAudit::Baseline.disposition(5, "pr_required")
    rescue ArgumentError => e
      e
    end
    assert(error, "expected ArgumentError for an unknown class")
  end

  # --- Evaluator -----------------------------------------------------------

  def test_evaluator_passes_a_required_setting_that_is_live
    row = RepoSettingsAudit::Evaluator.evaluate_setting(
      klass: 1, setting: "pr_required", live: true, has_ci: true
    )
    assert_equal("pass", row.fetch("status"))
  end

  def test_evaluator_fails_a_required_setting_that_is_missing
    row = RepoSettingsAudit::Evaluator.evaluate_setting(
      klass: 1, setting: "pr_required", live: false, has_ci: true
    )
    assert_equal("fail", row.fetch("status"))
  end

  def test_evaluator_warns_on_a_missing_recommended_setting
    row = RepoSettingsAudit::Evaluator.evaluate_setting(
      klass: 3, setting: "signed_commits", live: false, has_ci: true
    )
    assert_equal("warn", row.fetch("status"))
  end

  def test_evaluator_passes_a_present_recommended_setting
    row = RepoSettingsAudit::Evaluator.evaluate_setting(
      klass: 3, setting: "signed_commits", live: true, has_ci: true
    )
    assert_equal("pass", row.fetch("status"))
  end

  def test_evaluator_passes_class_one_linear_history_when_present
    row = RepoSettingsAudit::Evaluator.evaluate_setting(
      klass: 1, setting: "linear_history", live: true, has_ci: true
    )
    assert_equal("pass", row.fetch("status"))
  end

  def test_evaluator_warns_when_class_one_linear_history_is_absent
    row = RepoSettingsAudit::Evaluator.evaluate_setting(
      klass: 1, setting: "linear_history", live: false, has_ci: true
    )
    assert_equal("warn", row.fetch("status"))
  end

  def test_evaluator_rejects_linear_history_for_persistent_integration_override
    row = RepoSettingsAudit::Evaluator.evaluate_setting(
      klass: 3,
      setting: "linear_history",
      live: true,
      has_ci: true,
      overrides: { "linear_history" => "-" }
    )
    assert_equal("fail", row.fetch("status"))
  end

  def test_evaluator_marks_required_status_checks_na_when_repo_has_no_ci
    row = RepoSettingsAudit::Evaluator.evaluate_setting(
      klass: 1, setting: "required_status_checks", live: false, has_ci: false
    )
    assert_equal("na", row.fetch("status"))
  end

  def test_evaluator_no_ci_carveout_does_not_apply_to_other_settings
    row = RepoSettingsAudit::Evaluator.evaluate_setting(
      klass: 1, setting: "pr_required", live: false, has_ci: false
    )
    assert_equal("fail", row.fetch("status"))
  end

  def test_evaluator_evaluate_returns_a_row_per_setting_with_summary
    result = RepoSettingsAudit::Evaluator.evaluate(
      klass: 3,
      live: {
        "pr_required" => true,
        "deletion_blocked" => true,
        "force_push_blocked" => true,
        "required_status_checks" => false,
        "linear_history" => false,
        "signed_commits" => false,
        "copilot_code_review" => false,
        "review_thread_resolution" => false
      },
      has_ci: true
    )

    assert_equal(RepoSettingsAudit::Baseline::SETTINGS.length, result.fetch("settings").length)
    assert_equal({ "pass" => 3, "warn" => 3, "fail" => 3, "na" => 0 }, result.fetch("summary"))
  end

  def test_evaluator_reports_default_branch_drift_as_required
    row = RepoSettingsAudit::Evaluator.evaluate_setting(
      klass: 4, setting: "default_branch_main", live: false, has_ci: true
    )
    assert_equal("fail", row.fetch("status"))
  end

  # --- SettingsExtractor ---------------------------------------------------

  FULL_RULESET = {
    "enforcement" => "active",
    "conditions" => { "ref_name" => { "include" => ["~DEFAULT_BRANCH"], "exclude" => [] } },
    "rules" => [
      { "type" => "deletion" },
      { "type" => "non_fast_forward" },
      { "type" => "required_signatures" },
      { "type" => "pull_request", "parameters" => { "required_review_thread_resolution" => true } },
      { "type" => "copilot_code_review" },
      { "type" => "required_status_checks",
        "parameters" => { "required_status_checks" => [{ "context" => "ci" }] } }
    ]
  }.freeze

  FULL_RULESET_WITH_LINEAR = FULL_RULESET.merge(
    "rules" => FULL_RULESET.fetch("rules") + [{ "type" => "required_linear_history" }]
  ).freeze

  def test_extractor_derives_live_settings_from_an_applicable_active_ruleset
    extracted = RepoSettingsAudit::SettingsExtractor.extract(
      default_branch: "main", rulesets: [FULL_RULESET], classic_protection: nil
    )

    live = extracted.fetch("live")
    assert(live.fetch("deletion_blocked"))
    assert(live.fetch("force_push_blocked"))
    assert(live.fetch("signed_commits"))
    assert(live.fetch("pr_required"))
    assert(live.fetch("copilot_code_review"))
    assert(live.fetch("review_thread_resolution"))
    assert(live.fetch("required_status_checks"))
    refute(live.fetch("linear_history"), "linear_history rule was never included")
    refute(extracted.fetch("flags").fetch("dual_protection_systems"))
  end

  def test_extractor_ignores_a_ruleset_that_does_not_target_the_default_branch
    ruleset = FULL_RULESET.merge(
      "conditions" => { "ref_name" => { "include" => ["refs/heads/next"], "exclude" => [] } }
    )
    extracted = RepoSettingsAudit::SettingsExtractor.extract(
      default_branch: "main", rulesets: [ruleset], classic_protection: nil
    )

    refute(extracted.fetch("live").fetch("deletion_blocked"))
  end

  def test_extractor_ignores_a_disabled_ruleset
    ruleset = FULL_RULESET.merge("enforcement" => "disabled")
    extracted = RepoSettingsAudit::SettingsExtractor.extract(
      default_branch: "main", rulesets: [ruleset], classic_protection: nil
    )

    refute(extracted.fetch("live").fetch("deletion_blocked"))
  end

  def test_extractor_treats_an_empty_required_status_checks_list_as_unsatisfied
    ruleset = {
      "enforcement" => "active",
      "conditions" => { "ref_name" => { "include" => ["~DEFAULT_BRANCH"], "exclude" => [] } },
      "rules" => [
        { "type" => "required_status_checks", "parameters" => { "required_status_checks" => [] } }
      ]
    }
    extracted = RepoSettingsAudit::SettingsExtractor.extract(
      default_branch: "main", rulesets: [ruleset], classic_protection: nil
    )

    refute(extracted.fetch("live").fetch("required_status_checks"))
  end

  CLASSIC_PROTECTION = {
    "allow_deletions" => { "enabled" => false },
    "allow_force_pushes" => { "enabled" => false },
    "required_linear_history" => { "enabled" => true },
    "required_signatures" => { "enabled" => true },
    "required_pull_request_reviews" => { "required_approving_review_count" => 0 },
    "required_status_checks" => { "contexts" => ["ci"] },
    "required_conversation_resolution" => { "enabled" => true },
    "enforce_admins" => { "enabled" => true }
  }.freeze

  def test_extractor_derives_live_settings_from_classic_protection
    extracted = RepoSettingsAudit::SettingsExtractor.extract(
      default_branch: "main", rulesets: [], classic_protection: CLASSIC_PROTECTION
    )

    live = extracted.fetch("live")
    assert(live.fetch("deletion_blocked"))
    assert(live.fetch("force_push_blocked"))
    assert(live.fetch("linear_history"))
    assert(live.fetch("signed_commits"))
    assert(live.fetch("pr_required"))
    assert(live.fetch("required_status_checks"))
    assert(live.fetch("review_thread_resolution"))
    refute(live.fetch("copilot_code_review"), "classic protection cannot express Copilot code review")
    assert(extracted.fetch("flags").fetch("enforce_admins"))
  end

  def test_extractor_unions_ruleset_and_classic_protection_and_flags_dual_systems
    ruleset = {
      "enforcement" => "active",
      "conditions" => { "ref_name" => { "include" => ["~DEFAULT_BRANCH"], "exclude" => [] } },
      "rules" => [{ "type" => "pull_request" }]
    }
    classic = { "allow_deletions" => { "enabled" => false } }

    extracted = RepoSettingsAudit::SettingsExtractor.extract(
      default_branch: "main", rulesets: [ruleset], classic_protection: classic
    )

    assert(extracted.fetch("live").fetch("pr_required"), "ruleset-derived setting missing from union")
    assert(extracted.fetch("live").fetch("deletion_blocked"), "classic-derived setting missing from union")
    assert(extracted.fetch("flags").fetch("dual_protection_systems"))
  end

  # --- RepoAuditor ---------------------------------------------------------

  def resolver
    RepoSettingsAudit::ClassResolver.load(CLASSES_FILE)
  end

  def test_auditor_evaluates_a_conformant_class_one_repo
    client = FixtureClient.new(
      "/repos/z-shell/wiki" => { "default_branch" => "main" },
      "/repos/z-shell/wiki/rulesets" => [{ "id" => 1, "target" => "branch" }],
      "/repos/z-shell/wiki/rulesets/1" => {
        "enforcement" => "active",
        "conditions" => { "ref_name" => { "include" => ["~DEFAULT_BRANCH"], "exclude" => [] } },
        "rules" => [
          { "type" => "deletion" }, { "type" => "non_fast_forward" }, { "type" => "required_signatures" },
          { "type" => "pull_request", "parameters" => { "required_review_thread_resolution" => true } },
          { "type" => "copilot_code_review" },
          { "type" => "required_status_checks", "parameters" => { "required_status_checks" => [{ "context" => "ci" }] } }
        ]
      },
      "/repos/z-shell/wiki/branches/main/protection" => GitHubErrorResponse.new(status: 404),
      "/repos/z-shell/wiki/actions/workflows" => { "total_count" => 3 }
    )

    result = RepoSettingsAudit::RepoAuditor.audit(client: client, repo: "z-shell/wiki", class_resolver: resolver)

    assert_equal(1, result.fetch("class"))
    assert_equal("explicit", result.fetch("class_source"))
    assert_equal("main", result.fetch("default_branch"))
    assert(result.fetch("default_branch_is_main"))
    assert(result.fetch("has_ci"))
    assert_equal(0, result.fetch("summary").fetch("fail"))
  end

  def test_auditor_fails_a_missing_required_setting
    client = FixtureClient.new(
      "/repos/z-shell/zsh-lint" => { "default_branch" => "main" },
      "/repos/z-shell/zsh-lint/rulesets" => [],
      "/repos/z-shell/zsh-lint/branches/main/protection" => GitHubErrorResponse.new(status: 404),
      "/repos/z-shell/zsh-lint/actions/workflows" => { "total_count" => 2 }
    )

    result = RepoSettingsAudit::RepoAuditor.audit(client: client, repo: "z-shell/zsh-lint", class_resolver: resolver)

    assert_equal(2, result.fetch("class"))
    assert(result.fetch("summary").fetch("fail") > 0, "expected a class-2 repo with no rules to report failures")
  end

  def test_auditor_marks_required_status_checks_na_without_any_workflow_files
    client = FixtureClient.new(
      "/repos/z-shell/no-ci-plugin" => { "default_branch" => "main" },
      "/repos/z-shell/no-ci-plugin/rulesets" => [],
      "/repos/z-shell/no-ci-plugin/branches/main/protection" => GitHubErrorResponse.new(status: 404),
      "/repos/z-shell/no-ci-plugin/actions/workflows" => { "total_count" => 0 }
    )

    result = RepoSettingsAudit::RepoAuditor.audit(client: client, repo: "z-shell/no-ci-plugin", class_resolver: resolver)

    row = result.fetch("settings").find { |setting| setting.fetch("name") == "required_status_checks" }
    assert_equal("na", row.fetch("status"))
    refute(result.fetch("has_ci"))
  end

  # --- Inventory -------------------------------------------------------------

  def test_inventory_filters_out_forks_archived_and_private_repos
    client = FixtureClient.new(
      "/orgs/z-shell/repos?type=all&per_page=100" => [
        { "full_name" => "z-shell/keep-me", "fork" => false, "archived" => false, "visibility" => "public" },
        { "full_name" => "z-shell/a-fork", "fork" => true, "archived" => false, "visibility" => "public" },
        { "full_name" => "z-shell/archived-repo", "fork" => false, "archived" => true, "visibility" => "public" },
        { "full_name" => "z-shell/private-repo", "fork" => false, "archived" => false, "visibility" => "private" }
      ],
      "/repos/z-shell/keep-me" => { "default_branch" => "main" },
      "/repos/z-shell/keep-me/rulesets" => [],
      "/repos/z-shell/keep-me/branches/main/protection" => GitHubErrorResponse.new(status: 404),
      "/repos/z-shell/keep-me/actions/workflows" => { "total_count" => 0 }
    )

    results = RepoSettingsAudit::Inventory.new(client: client, org: "z-shell", class_resolver: resolver).run

    assert_equal(["z-shell/keep-me"], results.map { |result| result.fetch("repository") })
  end

  def test_inventory_reports_an_error_record_instead_of_raising
    client = FixtureClient.new(
      "/repos/z-shell/broken" => GitHubErrorResponse.new(status: 500, message: "boom")
    )

    results = RepoSettingsAudit::Inventory.new(
      client: client, org: "z-shell", repos: ["z-shell/broken"], class_resolver: resolver
    ).run

    assert_equal(1, results.length)
    assert_equal("z-shell/broken", results.first.fetch("repository"))
    refute(results.first.fetch("errors").empty?, "expected the failing repo to carry an error record")
  end

  # --- Renderer --------------------------------------------------------------

  def clean_result
    RepoSettingsAudit::RepoAuditor.audit(
      client: FixtureClient.new(
        "/repos/z-shell/wiki" => { "default_branch" => "main" },
        "/repos/z-shell/wiki/rulesets" => [{ "id" => 1, "target" => "branch" }],
        "/repos/z-shell/wiki/rulesets/1" => FULL_RULESET_WITH_LINEAR,
        "/repos/z-shell/wiki/branches/main/protection" => GitHubErrorResponse.new(status: 404),
        "/repos/z-shell/wiki/actions/workflows" => { "total_count" => 1 }
      ),
      repo: "z-shell/wiki",
      class_resolver: resolver
    )
  end

  def dirty_result
    RepoSettingsAudit::RepoAuditor.audit(
      client: FixtureClient.new(
        "/repos/z-shell/zsh-lint" => { "default_branch" => "main" },
        "/repos/z-shell/zsh-lint/rulesets" => [],
        "/repos/z-shell/zsh-lint/branches/main/protection" => GitHubErrorResponse.new(status: 404),
        "/repos/z-shell/zsh-lint/actions/workflows" => { "total_count" => 2 }
      ),
      repo: "z-shell/zsh-lint",
      class_resolver: resolver
    )
  end

  def test_renderer_json_reports_schema_and_repo_counts
    payload = JSON.parse(RepoSettingsAudit::Renderer.new.json([clean_result, dirty_result], org: "z-shell"))

    assert_equal("z-shell", payload.fetch("org"))
    assert_equal(2, payload.fetch("repos_scanned"))
    assert_equal(1, payload.fetch("repos_with_fail"))
  end

  def test_renderer_markdown_skips_a_clean_repo_by_default
    markdown = RepoSettingsAudit::Renderer.new.markdown([clean_result, dirty_result], include_clean: false)

    refute(markdown.include?("z-shell/wiki"))
    assert(markdown.include?("z-shell/zsh-lint"))
  end

  def test_renderer_markdown_includes_a_clean_repo_with_include_clean
    markdown = RepoSettingsAudit::Renderer.new.markdown([clean_result], include_clean: true)

    assert(markdown.include?("z-shell/wiki"))
  end

  # --- CLI ---------------------------------------------------------------

  def cli_client
    FixtureClient.new(
      "/repos/z-shell/wiki" => { "default_branch" => "main" },
      "/repos/z-shell/wiki/rulesets" => [{ "id" => 1, "target" => "branch" }],
      "/repos/z-shell/wiki/rulesets/1" => FULL_RULESET,
      "/repos/z-shell/wiki/branches/main/protection" => GitHubErrorResponse.new(status: 404),
      "/repos/z-shell/wiki/actions/workflows" => { "total_count" => 1 }
    )
  end

  def test_cli_requires_either_repo_or_all_repos
    status = RepoSettingsAudit::CLI.run([], client: cli_client, stdout: StringIO.new, stderr: StringIO.new)
    assert_equal(2, status)
  end

  def test_cli_rejects_both_repo_and_all_repos
    status = RepoSettingsAudit::CLI.run(
      ["--repo", "z-shell/wiki", "--all-repos"], client: cli_client, stdout: StringIO.new, stderr: StringIO.new
    )
    assert_equal(2, status)
  end

  def test_cli_rejects_a_malformed_repo_value
    status = RepoSettingsAudit::CLI.run(
      ["--repo", "not-owner-slash-repo"], client: cli_client, stdout: StringIO.new, stderr: StringIO.new
    )
    assert_equal(2, status)
  end

  def test_cli_runs_against_an_explicit_repo_and_writes_markdown
    stdout = StringIO.new
    status = RepoSettingsAudit::CLI.run(
      ["--repo", "z-shell/wiki", "--classes-file", CLASSES_FILE, "--include-clean"],
      client: cli_client, stdout: stdout, stderr: StringIO.new
    )
    assert_equal(0, status)
    assert(stdout.string.include?("z-shell/wiki"))
  end

  def test_cli_json_flag_emits_parseable_json
    stdout = StringIO.new
    status = RepoSettingsAudit::CLI.run(
      ["--repo", "z-shell/wiki", "--classes-file", CLASSES_FILE, "--json"],
      client: cli_client, stdout: stdout, stderr: StringIO.new
    )
    assert_equal(0, status)
    payload = JSON.parse(stdout.string)
    assert_equal(1, payload.fetch("repos_scanned"))
  end

  def test_cli_exits_1_when_a_repo_request_fails
    client = FixtureClient.new("/repos/z-shell/broken" => GitHubErrorResponse.new(status: 500))
    status = RepoSettingsAudit::CLI.run(
      ["--repo", "z-shell/broken", "--classes-file", CLASSES_FILE],
      client: client, stdout: StringIO.new, stderr: StringIO.new
    )
    assert_equal(1, status)
  end

  # --- CommunityHealth (#720) ----------------------------------------------

  EXCEPTIONS_FILE = File.expand_path("../../knowledge/domains/governance/data/template-exceptions.yml", __dir__)
  ORG_BUG_FORM = "a" * 40
  ORG_CONFIG = "b" * 40

  def org_defaults
    { ".github/ISSUE_TEMPLATE/01_bug_report.yml" => ORG_BUG_FORM, ".github/ISSUE_TEMPLATE/config.yml" => ORG_CONFIG }
  end

  def exceptions
    RepoSettingsAudit::CommunityHealth.new(
      repositories: {
        "z-shell/zsh-lint" => {
          "vendor_org_forms" => true,
          "exceptions" => [{ "path" => ".github/ISSUE_TEMPLATE/parser-gap.yml", "blob" => "c" * 40, "reason" => "intake" }]
        }
      }
    )
  end

  def write_exceptions(data)
    path = File.join(Dir.mktmpdir, "template-exceptions.yml")
    File.write(path, data.to_yaml)
    path
  end

  def load_error(data)
    RepoSettingsAudit::CommunityHealth.load(write_exceptions(data))
    nil
  rescue ArgumentError => e
    e
  end

  def test_community_health_matches_the_inherited_paths_only
    candidate = ->(path) { RepoSettingsAudit::CommunityHealth.candidate?(path) }

    [
      ".github/ISSUE_TEMPLATE/01_bug_report.yml", ".github/ISSUE_TEMPLATE/config.yml",
      ".github/PULL_REQUEST_TEMPLATE.md", ".github/PULL_REQUEST_TEMPLATE/promotion.md", "docs/pull_request_template.md",
      "docs/CODE_OF_CONDUCT.md", "docs/SECURITY.md", ".github/CONTRIBUTING.md", "contributing.md", "SUPPORT.md",
      ".github/FUNDING.yml", ".github/copilot-instructions.md"
    ].each { |path| assert(candidate.call(path), "expected #{path} to match") }
    [
      ".github/CODEOWNERS", "CODEOWNERS", "src/CONTRIBUTING.md", "docs/guide/SECURITY.md", "README.md",
      "docs/copilot-instructions.md", ".github/workflows/security.yml"
    ].each { |path| refute(candidate.call(path), "expected #{path} not to match") }
  end

  def test_community_health_reports_each_status
    files = {
      ".github/ISSUE_TEMPLATE/01_bug_report.yml" => ORG_BUG_FORM,
      ".github/ISSUE_TEMPLATE/config.yml" => "d" * 40,
      ".github/ISSUE_TEMPLATE/parser-gap.yml" => "c" * 40,
      ".github/copilot-instructions.md" => "e" * 40,
      "docs/SECURITY.md" => "f" * 40
    }
    result = exceptions.evaluate(repo: "z-shell/zsh-lint", files: files, org_defaults: org_defaults)
    statuses = result.fetch("files").to_h { |row| [row.fetch("path"), row.fetch("status")] }

    assert_equal("vendored", statuses.fetch(".github/ISSUE_TEMPLATE/01_bug_report.yml"))
    assert_equal("vendored_drift", statuses.fetch(".github/ISSUE_TEMPLATE/config.yml"))
    assert_equal("approved", statuses.fetch(".github/ISSUE_TEMPLATE/parser-gap.yml"))
    assert_equal("adapter", statuses.fetch(".github/copilot-instructions.md"))
    assert_equal("shadow", statuses.fetch("docs/SECURITY.md"))
    assert_equal(3, result.fetch("drift"))
  end

  def test_community_health_flags_a_changed_or_missing_exception
    changed = exceptions.evaluate(
      repo: "z-shell/zsh-lint", files: { ".github/ISSUE_TEMPLATE/parser-gap.yml" => "9" * 40 }, org_defaults: org_defaults
    )
    missing = exceptions.evaluate(repo: "z-shell/zsh-lint", files: {}, org_defaults: org_defaults)

    assert_equal(["exception_changed"], changed.fetch("files").map { |row| row.fetch("status") })
    assert_equal(["exception_missing"], missing.fetch("files").map { |row| row.fetch("status") })
    assert_equal(1, missing.fetch("drift"))
  end

  def test_community_health_treats_an_unlisted_repo_copy_as_shadow_and_marks_identical_content
    files = { ".github/ISSUE_TEMPLATE/01_bug_report.yml" => ORG_BUG_FORM, ".github/ISSUE_TEMPLATE/config.yml" => "d" * 40 }
    result = exceptions.evaluate(repo: "z-shell/some-plugin", files: files, org_defaults: org_defaults)

    assert_equal(%w[shadow shadow], result.fetch("files").map { |row| row.fetch("status") })
    assert_equal([true, false], result.fetch("files").map { |row| row.fetch("identical_to_org") })
    assert_equal(2, result.fetch("drift"))
  end

  def test_community_health_reports_no_drift_without_local_files
    result = exceptions.evaluate(repo: "z-shell/some-plugin", files: {}, org_defaults: org_defaults)

    assert_equal([], result.fetch("files"))
    assert_equal(0, result.fetch("drift"))
  end

  def test_community_health_loads_the_checked_in_exceptions
    manifest = RepoSettingsAudit::CommunityHealth.load(EXCEPTIONS_FILE)

    %w[z-shell/wiki z-shell/zi z-shell/zsh-lint].each do |repo|
      entry = manifest.entry_for(repo)
      assert(entry.fetch("vendor_org_forms"), "expected #{repo} to vendor the organization forms")
      refute(entry.fetch("exceptions").empty?, "expected #{repo} to list an exception")
    end
    assert_equal({ "vendor_org_forms" => false, "exceptions" => [] }, manifest.entry_for("z-shell/some-plugin"))
  end

  def test_community_health_load_rejects_invalid_entries
    entry = ->(exception) { { "version" => 1, "repositories" => { "z-shell/x" => { "exceptions" => [exception] } } } }
    good = { "path" => ".github/ISSUE_TEMPLATE/x.yml", "blob" => "c" * 40, "reason" => "intake" }

    assert(load_error("version" => 2, "repositories" => {}), "expected an unknown version to be rejected")
    assert(load_error("version" => 1, "repositories" => { "no-slash" => {} }), "expected OWNER/REPO to be required")
    assert(load_error(entry.call(good.merge("path" => "README.md"))), "expected a non community health path to be rejected")
    assert(load_error(entry.call(good.merge("blob" => "c0ffee"))), "expected a short blob id to be rejected")
    assert(load_error(entry.call(good.merge("reason" => " "))), "expected a missing reason to be rejected")
    assert(load_error("version" => 1, "repositories" => { "z-shell/x" => { "vendor_org_forms" => "yes" } }),
           "expected a non-boolean vendor_org_forms to be rejected")
    assert_equal(nil, load_error(entry.call(good)))
  end

  def test_community_health_tree_files_rejects_a_truncated_tree
    client = FixtureClient.new("/repos/z-shell/big/git/trees/main?recursive=1" => { "truncated" => true, "tree" => [] })
    error = begin
      RepoSettingsAudit::CommunityHealth.tree_files(client, "z-shell/big", "main")
    rescue RepoSettingsAudit::GitHubError => e
      e
    end

    assert(error, "expected a truncated tree to raise")
  end

  def community_health_routes(repo, tree)
    {
      "/repos/z-shell/.github" => { "default_branch" => "main" },
      "/repos/z-shell/.github/git/trees/main?recursive=1" => {
        "truncated" => false,
        "tree" => [
          { "path" => ".github/ISSUE_TEMPLATE/01_bug_report.yml", "type" => "blob", "sha" => ORG_BUG_FORM },
          { "path" => ".github/copilot-instructions.md", "type" => "blob", "sha" => "0" * 40 },
          { "path" => ".github/CODEOWNERS", "type" => "blob", "sha" => "1" * 40 }
        ]
      },
      "/repos/#{repo}" => { "default_branch" => "main" },
      "/repos/#{repo}/rulesets" => [],
      "/repos/#{repo}/branches/main/protection" => GitHubErrorResponse.new(status: 404),
      "/repos/#{repo}/actions/workflows" => { "total_count" => 0 },
      "/repos/#{repo}/git/trees/main?recursive=1" => { "truncated" => false, "tree" => tree }
    }
  end

  def test_community_health_org_defaults_exclude_the_adapter_and_codeowners
    client = FixtureClient.new(community_health_routes("z-shell/p", []))

    assert_equal({ ".github/ISSUE_TEMPLATE/01_bug_report.yml" => ORG_BUG_FORM },
                 RepoSettingsAudit::CommunityHealth.org_defaults(client, "z-shell"))
  end

  def test_cli_community_health_reports_drift_and_exits_0_without_fail_on_drift
    tree = [{ "path" => ".github/ISSUE_TEMPLATE/01_bug_report.yml", "type" => "blob", "sha" => ORG_BUG_FORM }]
    stdout = StringIO.new
    status = RepoSettingsAudit::CLI.run(
      ["--repo", "z-shell/p", "--classes-file", CLASSES_FILE, "--community-health", "--exceptions-file", EXCEPTIONS_FILE],
      client: FixtureClient.new(community_health_routes("z-shell/p", tree)), stdout: stdout, stderr: StringIO.new
    )

    assert_equal(0, status)
    assert(stdout.string.include?("`.github/ISSUE_TEMPLATE/01_bug_report.yml`: shadow, identical to the organization default"))
  end

  def test_cli_fail_on_drift_exits_1_on_drift_and_0_when_clean
    tree = [{ "path" => ".github/ISSUE_TEMPLATE/01_bug_report.yml", "type" => "blob", "sha" => ORG_BUG_FORM }]
    args = ["--repo", "z-shell/p", "--classes-file", CLASSES_FILE, "--community-health", "--exceptions-file", EXCEPTIONS_FILE,
            "--fail-on-drift", "--json"]
    drift = RepoSettingsAudit::CLI.run(args.dup, client: FixtureClient.new(community_health_routes("z-shell/p", tree)),
                                                 stdout: StringIO.new, stderr: StringIO.new)
    stdout = StringIO.new
    clean = RepoSettingsAudit::CLI.run(args.dup, client: FixtureClient.new(community_health_routes("z-shell/p", [])),
                                                 stdout: stdout, stderr: StringIO.new)

    assert_equal(1, drift)
    assert_equal(0, clean)
    assert_equal(0, JSON.parse(stdout.string).fetch("repos_with_community_health_drift"))
  end

  def test_cli_fail_on_drift_requires_community_health
    status = RepoSettingsAudit::CLI.run(
      ["--repo", "z-shell/wiki", "--fail-on-drift"], client: cli_client, stdout: StringIO.new, stderr: StringIO.new
    )
    assert_equal(2, status)
  end

  def test_cli_json_omits_the_community_health_counter_without_the_flag
    stdout = StringIO.new
    RepoSettingsAudit::CLI.run(
      ["--repo", "z-shell/wiki", "--classes-file", CLASSES_FILE, "--json"], client: cli_client, stdout: stdout, stderr: StringIO.new
    )
    refute(JSON.parse(stdout.string).key?("repos_with_community_health_drift"))
  end

  def test_auditor_skips_community_health_for_the_organization_repository
    routes = community_health_routes("z-shell/.github", [])
    routes["/repos/z-shell/.github"] = { "default_branch" => "main" }
    context = { exceptions: exceptions, org_defaults: org_defaults, org: "z-shell" }

    result = RepoSettingsAudit::RepoAuditor.audit(
      client: FixtureClient.new(routes), repo: "z-shell/.github", class_resolver: resolver, community_health: context
    )

    assert_equal(0, result.fetch("community_health").fetch("drift"))
    assert(result.fetch("community_health").key?("skipped"))
  end

  def test_auditor_records_a_tree_failure_as_an_error_and_keeps_settings
    routes = community_health_routes("z-shell/p", [])
    routes["/repos/z-shell/p/git/trees/main?recursive=1"] = GitHubErrorResponse.new(status: 409, message: "Git Repository is empty.")
    context = { exceptions: exceptions, org_defaults: org_defaults, org: "z-shell" }

    result = RepoSettingsAudit::RepoAuditor.audit(
      client: FixtureClient.new(routes), repo: "z-shell/p", class_resolver: resolver, community_health: context
    )

    assert_equal(1, result.fetch("errors").length)
    refute(result.fetch("settings").empty?, "expected the settings verdicts to remain")
  end
end

GitHubErrorResponse = Struct.new(:status, :message) do
  def initialize(status:, message: "GitHub API request failed")
    super(status, message)
  end
end

# A tiny injected stand-in for RepoSettingsAudit::GitHubClient: a fixed map of
# path => canned response. A GitHubErrorResponse value raises
# RepoSettingsAudit::GitHubError with that status instead of returning it.
class FixtureClient
  def initialize(routes)
    @routes = routes
  end

  def json(path)
    response = @routes.fetch(path) { raise "unexpected request: #{path}" }
    raise RepoSettingsAudit::GitHubError.new(response.message, status: response.status) if response.is_a?(GitHubErrorResponse)

    response
  end
end

tests = RepoSettingsAuditTest.new
methods = RepoSettingsAuditTest.instance_methods(false).grep(/^test_/).sort
failures = methods.filter_map do |method|
  tests.public_send(method)
  puts "PASS #{method}"
  nil
rescue StandardError => error
  warn "FAIL #{method}: #{error.message}"
  error
end

exit(failures.empty? ? 0 : 1)
