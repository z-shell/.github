#!/usr/bin/env ruby
# frozen_string_literal: true

require "json"
require "open3"
require "optparse"
require "yaml"

# Read-only audit that reports per-repository settings/ruleset drift against
# the decisions/0013-repository-settings-baseline.md baseline table, keyed by
# each repository's decisions/0007-release-publication-flow.md class (via
# knowledge/domains/governance/data/repository-classes.yml). Fulfills the rollout item from ADR-0013
# ("Build a read-only audit...") tracked on z-shell/.github#478. With
# --community-health it also reports shadow community health files against
# knowledge/domains/governance/data/template-exceptions.yml (z-shell/.github#720).
#
# Read-only by design: this script has no --apply/--confirm-apply mode. The
# settings changes recorded in #478 were hand-judged, per-repository ruleset
# mutations (removing one rule, adding specific status-check contexts) --
# meaningfully riskier and less uniform than the label create/update that
# automation/governance/labels-sync.rb automates. An apply mode is deliberately deferred to
# separate follow-up work rather than built here.
module RepoSettingsAudit
  SCHEMA = "z-shell/repo-settings-audit/v1"

  class GitHubError < StandardError
    attr_reader :status

    def initialize(message, status: nil)
      super(message)
      @status = status
    end
  end

  # Thin `gh api` wrapper, matching automation/ci/audit-scheduled-workflows.rb's
  # GitHubClient shape so tests can inject a fixture stand-in instead of
  # shelling out.
  class GitHubClient
    def initialize(runner: nil)
      @runner = runner || lambda { |command| Open3.capture3(*command) }
    end

    def json(path)
      command = ["gh", "api", "--method", "GET", path]
      stdout, stderr, status = @runner.call(command)
      return parse_json(stdout) if successful?(status)

      error = parse_error(stderr)
      raise GitHubError.new(error.fetch("message", "GitHub API request failed"), status: error["status"])
    end

    private

    def successful?(status)
      status.respond_to?(:success?) ? status.success? : status == true
    end

    def parse_json(body)
      parsed = JSON.parse(body)
      return parsed if parsed.is_a?(Array) || parsed.is_a?(Hash)

      raise GitHubError, "GitHub API response must be an object or array"
    rescue JSON::ParserError => error
      raise GitHubError, "GitHub API returned invalid JSON: #{error.message}"
    end

    def parse_error(body)
      parsed = JSON.parse(body)
      if parsed.is_a?(Hash)
        parsed["status"] ||= status_from(body)
        return parsed
      end

      { "message" => body.to_s.strip.empty? ? "GitHub API request failed" : body.to_s.strip, "status" => status_from(body) }
    rescue JSON::ParserError
      { "message" => body.to_s.strip.empty? ? "GitHub API request failed" : body.to_s.strip, "status" => status_from(body) }
    end

    def status_from(body)
      body.to_s[/HTTP\s+(\d{3})/, 1]&.to_i
    end
  end

  # Resolves a repository's decisions/0007-release-publication-flow.md class
  # from knowledge/domains/governance/data/repository-classes.yml, defaulting unlisted repositories to the
  # file's declared default_class rather than treating them as unclassified.
  class ClassResolver
    def self.load(path)
      data = YAML.safe_load_file(path, permitted_classes: [], permitted_symbols: [], aliases: false)
      raise ArgumentError, "#{path} must contain a mapping" unless data.is_a?(Hash)

      new(
        default_class: data.fetch("default_class"),
        repositories: data.fetch("repositories", {}),
        settings_overrides: data.fetch("settings_overrides", {})
      )
    end

    def initialize(default_class:, repositories:, settings_overrides: {})
      @default_class = default_class
      @repositories = repositories
      @settings_overrides = settings_overrides
    end

    def class_for(repo)
      @repositories.fetch(repo, @default_class)
    end

    def source_for(repo)
      @repositories.key?(repo) ? "explicit" : "default"
    end

    def settings_overrides_for(repo)
      @settings_overrides.fetch(repo, {})
    end
  end

  # The decisions/0013-repository-settings-baseline.md R/S/- table, expressed
  # per setting per class. Named repository exceptions are loaded from
  # knowledge/domains/governance/data/repository-classes.yml and override only the explicitly listed setting.
  class Baseline
    SETTINGS = %w[
      default_branch_main
      pr_required
      deletion_blocked
      force_push_blocked
      required_status_checks
      linear_history
      signed_commits
      copilot_code_review
      review_thread_resolution
    ].freeze

    TABLE = {
      1 => { "default_branch_main" => "R", "pr_required" => "R", "deletion_blocked" => "R", "force_push_blocked" => "R",
             "required_status_checks" => "R", "linear_history" => "S", "signed_commits" => "S",
             "copilot_code_review" => "R", "review_thread_resolution" => "R" },
      2 => { "default_branch_main" => "R", "pr_required" => "R", "deletion_blocked" => "R", "force_push_blocked" => "R",
             "required_status_checks" => "R", "linear_history" => "S", "signed_commits" => "S",
             "copilot_code_review" => "R", "review_thread_resolution" => "R" },
      3 => { "default_branch_main" => "R", "pr_required" => "R", "deletion_blocked" => "R", "force_push_blocked" => "R",
             "required_status_checks" => "R", "linear_history" => "S", "signed_commits" => "S",
             "copilot_code_review" => "S", "review_thread_resolution" => "R" },
      4 => { "default_branch_main" => "R", "pr_required" => "R", "deletion_blocked" => "R", "force_push_blocked" => "R",
             "required_status_checks" => "S", "linear_history" => "S", "signed_commits" => "S",
             "copilot_code_review" => "R", "review_thread_resolution" => "R" }
    }.freeze

    def self.disposition(klass, setting, overrides: {})
      row = TABLE.fetch(klass) { raise ArgumentError, "unknown ADR-0007 class: #{klass.inspect}" }
      baseline = row.fetch(setting) { raise ArgumentError, "unknown baseline setting: #{setting.inspect}" }
      overrides.fetch(setting, baseline)
    end
  end

  # Compares one repository's live, extracted settings against its class's
  # Baseline row and produces a pass/fail/warn/na verdict per setting.
  class Evaluator
    # required_status_checks is the baseline's own documented carve-out
    # (decisions/0013's "Repositories with no CI" section): unsatisfiable, so
    # reported as n/a rather than a failure, regardless of disposition.
    NO_CI_EXEMPT_SETTINGS = %w[required_status_checks].freeze

    def self.evaluate_setting(klass:, setting:, live:, has_ci:, overrides: {})
      disposition = Baseline.disposition(klass, setting, overrides: overrides)

      status =
        if NO_CI_EXEMPT_SETTINGS.include?(setting) && !has_ci
          "na"
        else
          status_for(disposition, live)
        end

      { "name" => setting, "disposition" => disposition, "live" => live, "status" => status }
    end

    def self.evaluate(klass:, live:, has_ci:, overrides: {})
      settings = Baseline::SETTINGS.map do |setting|
        evaluate_setting(
          klass: klass,
          setting: setting,
          live: live.fetch(setting, false),
          has_ci: has_ci,
          overrides: overrides
        )
      end

      summary = %w[pass fail warn na].to_h { |status| [status, settings.count { |row| row.fetch("status") == status }] }
      { "settings" => settings, "summary" => summary }
    end

    def self.status_for(disposition, live)
      case disposition
      when "R" then live ? "pass" : "fail"
      when "S" then live ? "pass" : "warn"
      when "-" then live ? "fail" : "pass"
      else raise ArgumentError, "unknown disposition: #{disposition.inspect}"
      end
    end
    private_class_method :status_for
  end

  # Normalizes live GitHub repository rulesets and classic branch protection
  # (decisions/0013's "the effective rule is their union" of both systems)
  # into the Baseline::SETTINGS boolean map, plus informational flags that
  # are not part of the R/S/- table but matter for the audit (enforce_admins,
  # and whether a repository still carries both protection systems at once).
  class SettingsExtractor
    RULE_TYPE_TO_SETTING = {
      "deletion" => "deletion_blocked",
      "non_fast_forward" => "force_push_blocked",
      "required_linear_history" => "linear_history",
      "required_signatures" => "signed_commits",
      "pull_request" => "pr_required",
      "copilot_code_review" => "copilot_code_review"
    }.freeze

    def self.extract(default_branch:, rulesets:, classic_protection:)
      applicable = rulesets.select { |ruleset| applies?(ruleset, default_branch) }
      from_rulesets = live_from_rulesets(applicable)
      from_classic = live_from_classic(classic_protection)

      live = Baseline::SETTINGS.to_h { |setting| [setting, from_rulesets.fetch(setting, false) || from_classic.fetch(setting, false)] }
      live["default_branch_main"] = default_branch == "main"

      {
        "live" => live,
        "flags" => {
          "dual_protection_systems" => !applicable.empty? && !classic_protection.nil?,
          "enforce_admins" => !!classic_protection&.dig("enforce_admins", "enabled")
        }
      }
    end

    def self.applies?(ruleset, default_branch)
      return false unless ruleset["enforcement"] == "active"

      ref = ruleset.dig("conditions", "ref_name") || {}
      include_patterns = Array(ref["include"])
      exclude_patterns = Array(ref["exclude"])
      target = "refs/heads/#{default_branch}"

      matched = include_patterns.any? { |pattern| ref_matches?(pattern, target, default_branch) }
      excluded = exclude_patterns.any? { |pattern| ref_matches?(pattern, target, default_branch) }
      matched && !excluded
    end

    def self.ref_matches?(pattern, target, default_branch)
      return true if pattern == "~DEFAULT_BRANCH"
      return true if pattern == "~ALL"
      return true if pattern == target

      File.fnmatch(pattern, target) || pattern == default_branch
    end

    def self.live_from_rulesets(rulesets)
      settings = {}
      rulesets.each do |ruleset|
        Array(ruleset["rules"]).each do |rule|
          setting = RULE_TYPE_TO_SETTING[rule["type"]]
          next unless setting

          settings[setting] = true
          settings["review_thread_resolution"] = true if review_thread_resolution?(rule)
        end

        checks = rulesets_status_checks(ruleset)
        settings["required_status_checks"] = true unless checks.empty?
      end
      settings
    end

    # review_thread_resolution is a parameter of the pull_request rule, not a
    # rule type of its own, so RULE_TYPE_TO_SETTING cannot carry it.
    def self.review_thread_resolution?(rule)
      rule["type"] == "pull_request" && rule.dig("parameters", "required_review_thread_resolution") == true
    end

    def self.rulesets_status_checks(ruleset)
      rule = Array(ruleset["rules"]).find { |candidate| candidate["type"] == "required_status_checks" }
      return [] unless rule

      Array(rule.dig("parameters", "required_status_checks"))
    end

    def self.live_from_classic(protection)
      return {} if protection.nil?

      {
        "deletion_blocked" => protection.dig("allow_deletions", "enabled") == false,
        "force_push_blocked" => protection.dig("allow_force_pushes", "enabled") == false,
        "linear_history" => !!protection.dig("required_linear_history", "enabled"),
        "signed_commits" => !!protection.dig("required_signatures", "enabled"),
        "pr_required" => !protection["required_pull_request_reviews"].nil?,
        "required_status_checks" => !Array(protection.dig("required_status_checks", "contexts")).empty?,
        "review_thread_resolution" => !!protection.dig("required_conversation_resolution", "enabled")
        # copilot_code_review is deliberately absent: classic protection has no
        # way to express it, so it must never contribute a true value for it.
      }
    end

    private_class_method :applies?, :ref_matches?, :live_from_rulesets, :review_thread_resolution?, :rulesets_status_checks,
                         :live_from_classic
  end

  # Shadow community health files (z-shell/.github#720). GitHub applies the
  # organization's community health files to every repository without a file
  # of its own, so a local copy hides the organization default. The approved
  # local files are recorded in
  # knowledge/domains/governance/data/template-exceptions.yml; everything else
  # this class matches is reported as drift. Report-only: the CLI exits
  # non-zero for drift only with --fail-on-drift.
  class CommunityHealth
    # Paths GitHub reads community health files from: the repository root,
    # .github/ or docs/. CODEOWNERS is not inherited from the organization,
    # so it is not a shadow file.
    PATH_PATTERN = %r{
      \A(?:\.github/|docs/)?
      (?:
        (?:ISSUE_TEMPLATE|PULL_REQUEST_TEMPLATE|DISCUSSION_TEMPLATE)/.+
        |
        (?:CONTRIBUTING|SECURITY|CODE_OF_CONDUCT|SUPPORT|GOVERNANCE|FUNDING|PULL_REQUEST_TEMPLATE|ISSUE_TEMPLATE)(?:\.[A-Za-z0-9]+)?
      )\z
    }ix
    ADAPTER_PATH = ".github/copilot-instructions.md"
    DRIFT_STATUSES = %w[shadow adapter exception_changed exception_missing vendored_drift].freeze
    STATUSES = (%w[approved vendored] + DRIFT_STATUSES).freeze
    BLOB_PATTERN = /\A[0-9a-f]{40}\z/

    def self.load(path)
      data = YAML.safe_load_file(path, permitted_classes: [], permitted_symbols: [], aliases: false)
      raise ArgumentError, "#{path} must contain a mapping" unless data.is_a?(Hash)
      raise ArgumentError, "#{path}: version must be 1" unless data["version"] == 1

      repositories = data.fetch("repositories", {})
      raise ArgumentError, "#{path}: repositories must be a mapping" unless repositories.is_a?(Hash)

      new(repositories: repositories.to_h { |repo, entry| [repo, normalize_entry(path, repo, entry)] })
    end

    def self.normalize_entry(path, repo, entry)
      raise ArgumentError, "#{path}: repository must be OWNER/REPO: #{repo}" unless repo.to_s.match?(%r{\A[^/]+/[^/]+\z})
      raise ArgumentError, "#{path}: #{repo} must be a mapping" unless entry.is_a?(Hash)

      vendor = entry.fetch("vendor_org_forms", false)
      raise ArgumentError, "#{path}: #{repo} vendor_org_forms must be true or false" unless [true, false].include?(vendor)

      exceptions = entry.fetch("exceptions", [])
      raise ArgumentError, "#{path}: #{repo} exceptions must be a list" unless exceptions.is_a?(Array)

      exceptions.each do |exception|
        raise ArgumentError, "#{path}: #{repo} exception must be a mapping" unless exception.is_a?(Hash)

        file = exception["path"].to_s
        raise ArgumentError, "#{path}: #{repo} #{file.inspect} is not a community health path" unless candidate?(file)
        raise ArgumentError, "#{path}: #{repo} #{file} blob must be a full 40-character id" unless exception["blob"].to_s.match?(BLOB_PATTERN)
        raise ArgumentError, "#{path}: #{repo} #{file} needs a reason" if exception["reason"].to_s.strip.empty?
      end
      paths = exceptions.map { |exception| exception["path"] }
      raise ArgumentError, "#{path}: #{repo} lists a path twice" unless paths.uniq.length == paths.length

      { "vendor_org_forms" => vendor, "exceptions" => exceptions }
    end

    def self.candidate?(path)
      path == ADAPTER_PATH || PATH_PATTERN.match?(path)
    end

    # Matching blobs (symbolic links included) at the default branch, as
    # path => blob id. A truncated tree cannot prove the absence of a file.
    def self.tree_files(client, repo, branch)
      tree = client.json("/repos/#{repo}/git/trees/#{branch}?recursive=1")
      raise GitHubError, "#{repo} tree response is truncated" if tree["truncated"]

      Array(tree["tree"]).select { |entry| entry["type"] == "blob" && candidate?(entry["path"]) }
                         .to_h { |entry| [entry.fetch("path"), entry.fetch("sha")] }
    end

    # The organization defaults: community health files of OWNER/.github,
    # without the Copilot adapter, which GitHub does not inherit.
    def self.org_defaults(client, org)
      repo = "#{org}/.github"
      branch = client.json("/repos/#{repo}").fetch("default_branch", "main")
      tree_files(client, repo, branch).reject { |path, _blob| path == ADAPTER_PATH }
    end

    def initialize(repositories:)
      @repositories = repositories
    end

    def entry_for(repo)
      @repositories.fetch(repo, { "vendor_org_forms" => false, "exceptions" => [] })
    end

    def evaluate(repo:, files:, org_defaults:)
      entry = entry_for(repo)
      approved = entry.fetch("exceptions").to_h { |exception| [exception.fetch("path"), exception] }

      rows = files.sort.map do |path, blob|
        row = { "path" => path, "blob" => blob, "status" => status_for(path, blob, entry, approved, org_defaults) }
        row["identical_to_org"] = org_defaults[path] == blob if org_defaults.key?(path)
        row
      end
      approved.each_key do |path|
        rows << { "path" => path, "blob" => nil, "status" => "exception_missing" } unless files.key?(path)
      end

      summary = STATUSES.to_h { |status| [status, rows.count { |row| row.fetch("status") == status }] }
      { "files" => rows, "summary" => summary, "drift" => DRIFT_STATUSES.sum { |status| summary.fetch(status) } }
    end

    private

    def status_for(path, blob, entry, approved, org_defaults)
      return approved.fetch(path).fetch("blob") == blob ? "approved" : "exception_changed" if approved.key?(path)
      return "adapter" if path == ADAPTER_PATH
      return org_defaults.fetch(path) == blob ? "vendored" : "vendored_drift" if entry.fetch("vendor_org_forms") && org_defaults.key?(path)

      "shadow"
    end
  end

  # Fetches one repository's live rulesets and classic protection, extracts
  # its settings, and evaluates them against its Baseline row.
  class RepoAuditor
    # community_health, when given, is { exceptions: CommunityHealth,
    # org_defaults: { path => blob }, org: "z-shell" } and adds a
    # community_health section to the result.
    def self.audit(client:, repo:, class_resolver:, community_health: nil)
      repository = client.json("/repos/#{repo}")
      default_branch = repository.fetch("default_branch", "main")

      rulesets = branch_ruleset_details(client, repo)
      classic_protection = fetch_classic_protection(client, repo, default_branch)
      has_ci = fetch_workflow_count(client, repo).positive?

      extracted = SettingsExtractor.extract(default_branch: default_branch, rulesets: rulesets, classic_protection: classic_protection)
      klass = class_resolver.class_for(repo)
      evaluation = Evaluator.evaluate(
        klass: klass,
        live: extracted.fetch("live"),
        has_ci: has_ci,
        overrides: class_resolver.settings_overrides_for(repo)
      )

      result = {
        "schema" => SCHEMA,
        "repository" => repo,
        "class" => klass,
        "class_source" => class_resolver.source_for(repo),
        "default_branch" => default_branch,
        "default_branch_is_main" => default_branch == "main",
        "has_ci" => has_ci,
        "settings" => evaluation.fetch("settings"),
        "summary" => evaluation.fetch("summary"),
        "flags" => extracted.fetch("flags"),
        "errors" => []
      }
      add_community_health(result, client, repo, default_branch, community_health) if community_health
      result
    end

    # The organization repository is the source of the defaults, so it is
    # not evaluated against them. A failed tree request is recorded as an
    # error on this repository and leaves its settings verdicts intact.
    def self.add_community_health(result, client, repo, default_branch, community_health)
      if repo == "#{community_health.fetch(:org)}/.github"
        result["community_health"] = { "skipped" => "organization default source", "files" => [], "summary" => {}, "drift" => 0 }
        return
      end

      files = CommunityHealth.tree_files(client, repo, default_branch)
      result["community_health"] = community_health.fetch(:exceptions).evaluate(
        repo: repo, files: files, org_defaults: community_health.fetch(:org_defaults)
      )
    rescue GitHubError => error
      result["errors"] << { "status" => error.status, "message" => error.message }
    end

    def self.branch_ruleset_details(client, repo)
      summaries = client.json("/repos/#{repo}/rulesets")
      raise GitHubError, "rulesets response must be an array" unless summaries.is_a?(Array)

      summaries.select { |summary| summary["target"] == "branch" }.map do |summary|
        client.json("/repos/#{repo}/rulesets/#{summary.fetch("id")}")
      end
    end

    def self.fetch_classic_protection(client, repo, default_branch)
      client.json("/repos/#{repo}/branches/#{default_branch}/protection")
    rescue GitHubError => error
      return nil if error.status == 404

      raise
    end

    def self.fetch_workflow_count(client, repo)
      client.json("/repos/#{repo}/actions/workflows").fetch("total_count", 0)
    end

    private_class_method :add_community_health, :branch_ruleset_details, :fetch_classic_protection, :fetch_workflow_count
  end

  # Enumerates target repositories -- an explicit list, or every active,
  # public, non-fork repository in the org, matching the scope PR #474 and
  # issue #478's manual audits both used -- and audits each with RepoAuditor.
  # A single repository's failure becomes an error record, not a crash: one
  # broken `gh api` call must not blank out the rest of the org's results.
  class Inventory
    def initialize(client:, org:, class_resolver:, repos: nil, community_health: nil)
      @client = client
      @org = org
      @class_resolver = class_resolver
      @repos = repos
      @community_health = community_health
    end

    def run
      target_repos.map do |repo|
        RepoAuditor.audit(client: @client, repo: repo, class_resolver: @class_resolver, community_health: @community_health)
      rescue GitHubError => error
        error_record(repo, error)
      end
    end

    private

    def target_repos
      return @repos if @repos

      repositories.reject { |repository| repository["fork"] || repository["archived"] || repository["visibility"] != "public" }
                  .map { |repository| repository.fetch("full_name") }
    end

    def repositories
      page = 1
      repositories = []
      loop do
        suffix = page == 1 ? "" : "&page=#{page}"
        response = @client.json("/orgs/#{@org}/repos?type=all&per_page=100#{suffix}")
        raise GitHubError, "org repos response must be an array" unless response.is_a?(Array)

        repositories.concat(response)
        break if response.length < 100

        page += 1
      end
      repositories
    end

    def error_record(repo, error)
      {
        "schema" => SCHEMA,
        "repository" => repo,
        "class" => nil,
        "class_source" => nil,
        "default_branch" => nil,
        "default_branch_is_main" => nil,
        "has_ci" => nil,
        "settings" => [],
        "summary" => { "pass" => 0, "fail" => 0, "warn" => 0, "na" => 0 },
        "flags" => {},
        "errors" => [{ "status" => error.status, "message" => error.message }]
      }
    end
  end

  # Renders Inventory#run results as JSON (machine-readable) or Markdown
  # (the human-review default). Markdown skips conformant repositories by
  # default -- the point is to surface drift, not to restate a clean bill of
  # health for every repository in the org.
  class Renderer
    def json(results, org:)
      payload = {
        "schema" => SCHEMA,
        "org" => org,
        "repos_scanned" => results.length,
        "repos_with_fail" => results.count { |result| result.fetch("summary").fetch("fail") > 0 },
        "repos_with_errors" => results.count { |result| !result.fetch("errors").empty? }
      }
      if results.any? { |result| result.key?("community_health") }
        payload["repos_with_community_health_drift"] = results.count { |result| community_health_drift(result).positive? }
      end
      payload["results"] = results
      JSON.pretty_generate(payload) + "\n"
    end

    def self.community_health_drift(result)
      result.dig("community_health", "drift").to_i
    end

    def markdown(results, include_clean:)
      lines = ["# Repository Settings Audit", "", "Baseline: decisions/0013-repository-settings-baseline.md", ""]
      results.each do |result|
        next if clean?(result) && !include_clean

        lines.concat(repo_section(result))
      end
      lines.join("\n") + "\n"
    end

    private

    def community_health_drift(result)
      self.class.community_health_drift(result)
    end

    def clean?(result)
      result.fetch("errors").empty? && result.fetch("summary").fetch("fail").zero? && result.fetch("summary").fetch("warn").zero? &&
        community_health_drift(result).zero?
    end

    def repo_section(result)
      lines = ["## #{result.fetch("repository")} (class #{result.fetch("class") || "unknown"})", ""]

      unless result.fetch("errors").empty?
        lines << "**Request failed:**"
        result.fetch("errors").each { |error| lines << "- #{error.fetch("message")}" }
        lines << ""
        return lines
      end

      if clean?(result)
        lines << "Clean: no failing or recommended settings missing."
        lines << ""
        return lines
      end

      fail_rows = result.fetch("settings").select { |row| row.fetch("status") == "fail" }
      warn_rows = result.fetch("settings").select { |row| row.fetch("status") == "warn" }

      unless fail_rows.empty?
        lines << "**FAIL (required by ADR-0013, not satisfied):**"
        fail_rows.each { |row| lines << "- #{row.fetch("name")}" }
        lines << ""
      end

      unless warn_rows.empty?
        lines << "**WARN (recommended, not satisfied):**"
        warn_rows.each { |row| lines << "- #{row.fetch("name")}" }
        lines << ""
      end

      if community_health_drift(result).positive?
        lines << "**Community health drift (z-shell/.github#720):**"
        result.fetch("community_health").fetch("files").each do |row|
          next unless CommunityHealth::DRIFT_STATUSES.include?(row.fetch("status"))

          identical = row["identical_to_org"] ? ", identical to the organization default" : ""
          lines << "- `#{row.fetch("path")}`: #{row.fetch("status")}#{identical}"
        end
        lines << ""
      end

      notes = []
      notes << "default branch is `#{result.fetch("default_branch")}`, not `main` (audit-only)" unless result.fetch("default_branch_is_main")
      notes << "both a ruleset and classic branch protection are active" if result.fetch("flags")["dual_protection_systems"]
      notes << "`enforce_admins` is enabled" if result.fetch("flags")["enforce_admins"]
      unless notes.empty?
        lines << "**Notes:**"
        notes.each { |note| lines << "- #{note}" }
        lines << ""
      end

      lines
    end
  end

  class CLI
    def self.run(argv, client: GitHubClient.new, stdout: $stdout, stderr: $stderr)
      options = { org: "z-shell", repos: [], all_repos: false, json: false, include_clean: false,
                  community_health: false, fail_on_drift: false,
                  classes_file: File.expand_path("../../knowledge/domains/governance/data/repository-classes.yml", __dir__),
                  exceptions_file: File.expand_path("../../knowledge/domains/governance/data/template-exceptions.yml", __dir__) }
      parser = build_parser(options)
      parser.parse!(argv)

      validate!(options)

      class_resolver = ClassResolver.load(options[:classes_file])
      community_health = community_health_context(client, options) if options[:community_health]
      inventory = Inventory.new(
        client: client, org: options[:org], class_resolver: class_resolver,
        repos: options[:all_repos] ? nil : options[:repos], community_health: community_health
      )
      results = inventory.run

      renderer = Renderer.new
      rendered = options[:json] ? renderer.json(results, org: options[:org]) : renderer.markdown(results, include_clean: options[:include_clean])
      stdout.write(rendered)

      return 1 if results.any? { |result| !result.fetch("errors").empty? }
      return 1 if options[:fail_on_drift] && results.any? { |result| Renderer.community_health_drift(result).positive? }

      0
    rescue OptionParser::ParseError, ArgumentError => error
      stderr.puts error.message
      2
    rescue GitHubError => error
      stderr.puts "organization community health defaults: #{error.message}"
      1
    end

    def self.community_health_context(client, options)
      {
        exceptions: CommunityHealth.load(options[:exceptions_file]),
        org_defaults: CommunityHealth.org_defaults(client, options[:org]),
        org: options[:org]
      }
    end

    def self.build_parser(options)
      OptionParser.new do |option|
        option.on("--org ORG", "GitHub organization (default: z-shell)") { |value| options[:org] = value }
        option.on("--repo OWNER/REPO", "Repository to audit; may be repeated") { |value| options[:repos] << value }
        option.on("--all-repos", "Audit every active, public, non-fork repository in --org") { options[:all_repos] = true }
        option.on("--classes-file PATH", "Repository class mapping (default: knowledge/domains/governance/data/repository-classes.yml)") { |value| options[:classes_file] = value }
        option.on("--json", "Emit JSON instead of Markdown") { options[:json] = true }
        option.on("--include-clean", "Include conformant repos in Markdown output") { options[:include_clean] = true }
        option.on("--community-health", "Also report shadow community health files and Copilot adapters (#720)") { options[:community_health] = true }
        option.on("--exceptions-file PATH", "Approved local files (default: knowledge/domains/governance/data/template-exceptions.yml)") do |value|
          options[:exceptions_file] = value
        end
        option.on("--fail-on-drift", "Exit 1 when --community-health finds drift (default: report only)") { options[:fail_on_drift] = true }
      end
    end

    def self.validate!(options)
      if options[:all_repos] && !options[:repos].empty?
        raise OptionParser::InvalidOption, "use either --all-repos or one or more --repo values, not both"
      end
      raise OptionParser::MissingArgument, "pass at least one --repo OWNER/REPO or --all-repos" if !options[:all_repos] && options[:repos].empty?
      raise OptionParser::InvalidOption, "--fail-on-drift needs --community-health" if options[:fail_on_drift] && !options[:community_health]

      options[:repos].each do |repo|
        raise OptionParser::InvalidArgument, "--repo must be OWNER/REPO: #{repo}" unless repo.match?(%r{\A[^/]+/[^/]+\z})
      end
    end

    private_class_method :build_parser, :validate!, :community_health_context
  end
end

exit(RepoSettingsAudit::CLI.run(ARGV)) if $PROGRAM_NAME == __FILE__
