#!/usr/bin/env ruby
# frozen_string_literal: true

require "json"
require "open3"
require "optparse"
require "yaml"

# Read-only audit that reports per-repository settings/ruleset drift against
# the decisions/0013-repository-settings-baseline.md baseline table, keyed by
# each repository's decisions/0007-release-publication-flow.md class (via
# lib/repository-classes.yml). Fulfills the rollout item from ADR-0013
# ("Build a read-only audit...") tracked on z-shell/.github#478.
#
# Read-only by design: this script has no --apply/--confirm-apply mode. The
# settings changes recorded in #478 were hand-judged, per-repository ruleset
# mutations (removing one rule, adding specific status-check contexts) --
# meaningfully riskier and less uniform than the label create/update that
# scripts/labels-sync.rb automates. An apply mode is deliberately deferred to
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

  # Thin `gh api` wrapper, matching scripts/audit-scheduled-workflows.rb's
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
  # from lib/repository-classes.yml, defaulting unlisted repositories to the
  # file's declared default_class rather than treating them as unclassified.
  class ClassResolver
    def self.load(path)
      data = YAML.safe_load_file(path, permitted_classes: [], permitted_symbols: [], aliases: false)
      raise ArgumentError, "#{path} must contain a mapping" unless data.is_a?(Hash)

      new(default_class: data.fetch("default_class"), repositories: data.fetch("repositories", {}))
    end

    def initialize(default_class:, repositories:)
      @default_class = default_class
      @repositories = repositories
    end

    def class_for(repo)
      @repositories.fetch(repo, @default_class)
    end

    def source_for(repo)
      @repositories.key?(repo) ? "explicit" : "default"
    end
  end

  # The decisions/0013-repository-settings-baseline.md R/S/- table, expressed
  # per setting per class. "-" appears only for class 1's linear_history: not
  # required, not recommended, and per the ADR's own rationale actively
  # contradicts the next -> main promotion model when present.
  class Baseline
    SETTINGS = %w[
      pr_required
      deletion_blocked
      force_push_blocked
      required_status_checks
      linear_history
      signed_commits
      copilot_code_review
    ].freeze

    TABLE = {
      1 => { "pr_required" => "R", "deletion_blocked" => "R", "force_push_blocked" => "R",
             "required_status_checks" => "R", "linear_history" => "-", "signed_commits" => "S",
             "copilot_code_review" => "R" },
      2 => { "pr_required" => "R", "deletion_blocked" => "R", "force_push_blocked" => "R",
             "required_status_checks" => "R", "linear_history" => "S", "signed_commits" => "S",
             "copilot_code_review" => "R" },
      3 => { "pr_required" => "R", "deletion_blocked" => "R", "force_push_blocked" => "R",
             "required_status_checks" => "S", "linear_history" => "S", "signed_commits" => "S",
             "copilot_code_review" => "S" },
      4 => { "pr_required" => "R", "deletion_blocked" => "R", "force_push_blocked" => "R",
             "required_status_checks" => "S", "linear_history" => "S", "signed_commits" => "S",
             "copilot_code_review" => "R" }
    }.freeze

    def self.disposition(klass, setting)
      row = TABLE.fetch(klass) { raise ArgumentError, "unknown ADR-0007 class: #{klass.inspect}" }
      row.fetch(setting) { raise ArgumentError, "unknown baseline setting: #{setting.inspect}" }
    end
  end

  # Compares one repository's live, extracted settings against its class's
  # Baseline row and produces a pass/fail/warn/na verdict per setting.
  class Evaluator
    # required_status_checks is the baseline's own documented carve-out
    # (decisions/0013's "Repositories with no CI" section): unsatisfiable, so
    # reported as n/a rather than a failure, regardless of disposition.
    NO_CI_EXEMPT_SETTINGS = %w[required_status_checks].freeze

    def self.evaluate_setting(klass:, setting:, live:, has_ci:)
      disposition = Baseline.disposition(klass, setting)

      status =
        if NO_CI_EXEMPT_SETTINGS.include?(setting) && !has_ci
          "na"
        else
          status_for(disposition, live)
        end

      { "name" => setting, "disposition" => disposition, "live" => live, "status" => status }
    end

    def self.evaluate(klass:, live:, has_ci:)
      settings = Baseline::SETTINGS.map do |setting|
        evaluate_setting(klass: klass, setting: setting, live: live.fetch(setting, false), has_ci: has_ci)
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
        end

        checks = rulesets_status_checks(ruleset)
        settings["required_status_checks"] = true unless checks.empty?
      end
      settings
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
        "required_status_checks" => !Array(protection.dig("required_status_checks", "contexts")).empty?
        # copilot_code_review is deliberately absent: classic protection has no
        # way to express it, so it must never contribute a true value for it.
      }
    end

    private_class_method :applies?, :ref_matches?, :live_from_rulesets, :rulesets_status_checks, :live_from_classic
  end

  # Fetches one repository's live rulesets and classic protection, extracts
  # its settings, and evaluates them against its Baseline row.
  class RepoAuditor
    def self.audit(client:, repo:, class_resolver:)
      repository = client.json("/repos/#{repo}")
      default_branch = repository.fetch("default_branch", "main")

      rulesets = branch_ruleset_details(client, repo)
      classic_protection = fetch_classic_protection(client, repo, default_branch)
      has_ci = fetch_workflow_count(client, repo).positive?

      extracted = SettingsExtractor.extract(default_branch: default_branch, rulesets: rulesets, classic_protection: classic_protection)
      klass = class_resolver.class_for(repo)
      evaluation = Evaluator.evaluate(klass: klass, live: extracted.fetch("live"), has_ci: has_ci)

      {
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

    private_class_method :branch_ruleset_details, :fetch_classic_protection, :fetch_workflow_count
  end

  # Enumerates target repositories -- an explicit list, or every active,
  # public, non-fork repository in the org, matching the scope PR #474 and
  # issue #478's manual audits both used -- and audits each with RepoAuditor.
  # A single repository's failure becomes an error record, not a crash: one
  # broken `gh api` call must not blank out the rest of the org's results.
  class Inventory
    def initialize(client:, org:, class_resolver:, repos: nil)
      @client = client
      @org = org
      @class_resolver = class_resolver
      @repos = repos
    end

    def run
      target_repos.map do |repo|
        RepoAuditor.audit(client: @client, repo: repo, class_resolver: @class_resolver)
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
      JSON.pretty_generate(
        "schema" => SCHEMA,
        "org" => org,
        "repos_scanned" => results.length,
        "repos_with_fail" => results.count { |result| result.fetch("summary").fetch("fail") > 0 },
        "repos_with_errors" => results.count { |result| !result.fetch("errors").empty? },
        "results" => results
      ) + "\n"
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

    def clean?(result)
      result.fetch("errors").empty? && result.fetch("summary").fetch("fail").zero? && result.fetch("summary").fetch("warn").zero?
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
                  classes_file: File.expand_path("../lib/repository-classes.yml", __dir__) }
      parser = build_parser(options)
      parser.parse!(argv)

      validate!(options)

      class_resolver = ClassResolver.load(options[:classes_file])
      inventory = Inventory.new(
        client: client, org: options[:org], class_resolver: class_resolver,
        repos: options[:all_repos] ? nil : options[:repos]
      )
      results = inventory.run

      renderer = Renderer.new
      rendered = options[:json] ? renderer.json(results, org: options[:org]) : renderer.markdown(results, include_clean: options[:include_clean])
      stdout.write(rendered)

      results.any? { |result| !result.fetch("errors").empty? } ? 1 : 0
    rescue OptionParser::ParseError, ArgumentError => error
      stderr.puts error.message
      2
    end

    def self.build_parser(options)
      OptionParser.new do |option|
        option.on("--org ORG", "GitHub organization (default: z-shell)") { |value| options[:org] = value }
        option.on("--repo OWNER/REPO", "Repository to audit; may be repeated") { |value| options[:repos] << value }
        option.on("--all-repos", "Audit every active, public, non-fork repository in --org") { options[:all_repos] = true }
        option.on("--classes-file PATH", "Repository class mapping (default: lib/repository-classes.yml)") { |value| options[:classes_file] = value }
        option.on("--json", "Emit JSON instead of Markdown") { options[:json] = true }
        option.on("--include-clean", "Include conformant repos in Markdown output") { options[:include_clean] = true }
      end
    end

    def self.validate!(options)
      if options[:all_repos] && !options[:repos].empty?
        raise OptionParser::InvalidOption, "use either --all-repos or one or more --repo values, not both"
      end
      raise OptionParser::MissingArgument, "pass at least one --repo OWNER/REPO or --all-repos" if !options[:all_repos] && options[:repos].empty?

      options[:repos].each do |repo|
        raise OptionParser::InvalidArgument, "--repo must be OWNER/REPO: #{repo}" unless repo.match?(%r{\A[^/]+/[^/]+\z})
      end
    end

    private_class_method :build_parser, :validate!
  end
end

exit(RepoSettingsAudit::CLI.run(ARGV)) if $PROGRAM_NAME == __FILE__
