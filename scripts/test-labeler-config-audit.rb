#!/usr/bin/env ruby
# frozen_string_literal: true

require "json"
require "stringio"

require_relative "labeler-config-audit"

# A stand-in for LabelerConfigAudit::GitHubClient. Maps "repo:path" to either a
# config body or :missing, and mimics `gh api` well enough to exercise the
# 404-is-not-a-finding path.
class FixtureClient
  def initialize(files)
    @files = files
  end

  def file(repo, path)
    entry = @files["#{repo}:#{path}"]
    return nil if entry.nil? || entry == :missing

    raise LabelerConfigAudit::GitHubError.new(entry.fetch(:message), status: entry[:status]) if entry.is_a?(Hash)

    entry
  end
end

class LabelerConfigAuditTest
  LABELS_FILE = File.expand_path("../lib/labels.yml", __dir__)
  V4_CONFIG = <<~YAML
    "documentation 📝":
      - "docs/*.md"
    area:ci:
      - ".github/workflows/*.yml"
  YAML
  V5_CONFIG = <<~YAML
    "enhancement ✨":
      - any:
          - changed-files:
              - any-glob-to-any-file: "lib/**"
    type:bug:
      - any:
          - changed-files:
              - any-glob-to-any-file: "src/**"
  YAML

  def assert_equal(expected, actual)
    raise "expected #{expected.inspect}, got #{actual.inspect}" unless expected == actual
  end

  def assert(value, message = "expected truthy value")
    raise message unless value
  end

  def canonical
    LabelerConfigAudit.canonical_labels(LABELS_FILE)
  end

  def legacy
    LabelerConfigAudit.legacy_map(LABELS_FILE)
  end

  def audit(repo, files)
    LabelerConfigAudit.audit_repo(repo, client: FixtureClient.new(files), canonical: canonical, legacy: legacy)
  end

  # A repository with no labeler config is not a finding. Reporting it as one
  # would make the audit noisy enough to be ignored.
  def test_missing_config_is_not_a_finding
    result = audit("z-shell/none", {})
    assert_equal(nil, result.fetch("config"))
    assert_equal(0, result.fetch("summary").fetch("unknown"))
  end

  def test_yaml_extension_is_also_read
    files = { "z-shell/alt:.github/labeler.yaml" => "area:docs:\n  - \"docs/**\"\n" }
    result = audit("z-shell/alt", files)
    assert_equal(true, result.fetch("config"))
    assert_equal(0, result.fetch("summary").fetch("unknown"))
  end

  def test_canonical_only_config_is_clean
    files = { "z-shell/clean:.github/labeler.yml" => "area:ci:\n  - \".github/**\"\ntype:docs:\n  - \"docs/**\"\n" }
    assert_equal(0, audit("z-shell/clean", files).fetch("summary").fetch("unknown"))
  end

  # The reason this audit exists: a legacy key is reported with the canonical
  # replacement so the fix is mechanical.
  def test_legacy_key_reports_its_replacement
    files = { "z-shell/drift:.github/labeler.yml" => V4_CONFIG }
    result = audit("z-shell/drift", files)
    assert_equal(1, result.fetch("summary").fetch("unknown"))
    entry = result.fetch("unknown").first
    assert_equal("documentation 📝", entry.fetch("label"))
    assert_equal("type:docs", entry.fetch("replacement"))
  end

  # An unknown key with no recorded migration still has to be reported, with a
  # null replacement rather than a guess.
  def test_unmapped_key_reports_nil_replacement
    files = { "z-shell/odd:.github/labeler.yml" => "plugin 🧿:\n  - \"*.zsh\"\n" }
    entry = audit("z-shell/odd", files).fetch("unknown").first
    assert_equal("plugin 🧿", entry.fetch("label"))
    assert_equal(nil, entry.fetch("replacement"))
  end

  # actions/labeler v5 nests globs under any/all. Only top-level keys are label
  # names, so the nested structure must not leak into the findings.
  def test_v5_schema_reads_only_top_level_keys
    files = { "z-shell/v5:.github/labeler.yml" => V5_CONFIG }
    result = audit("z-shell/v5", files)
    assert_equal(1, result.fetch("summary").fetch("unknown"))
    assert_equal("enhancement ✨", result.fetch("unknown").first.fetch("label"))
  end

  def test_invalid_yaml_raises
    files = { "z-shell/bad:.github/labeler.yml" => "a:\n  - b\n :\t- oops\n" }
    audit("z-shell/bad", files)
    raise "expected GitHubError"
  rescue LabelerConfigAudit::GitHubError => error
    assert(error.message.include?("not valid YAML"), "unexpected message: #{error.message}")
  end

  def test_non_mapping_config_is_malformed
    files = { "z-shell/list:.github/labeler.yml" => "- type:bug\n" }
    audit("z-shell/list", files)
    raise "expected GitHubError"
  rescue LabelerConfigAudit::GitHubError => error
    assert(error.message.include?("must be a mapping"), "unexpected message: #{error.message}")
  end

  def test_empty_label_key_is_malformed
    files = { "z-shell/empty:.github/labeler.yml" => "\"\":\n  - '*.rb'\n" }
    audit("z-shell/empty", files)
    raise "expected GitHubError"
  rescue LabelerConfigAudit::GitHubError => error
    assert(error.message.include?("non-empty strings"), "unexpected message: #{error.message}")
  end

  def test_json_output_and_exit_code_on_drift
    io = StringIO.new
    code = LabelerConfigAudit.run(
      ["--repo", "z-shell/drift", "--json", "--labels-file", LABELS_FILE],
      io: io,
      client: FixtureClient.new("z-shell/drift:.github/labeler.yml" => V4_CONFIG)
    )
    assert_equal(1, code)
    payload = JSON.parse(io.string)
    assert_equal(LabelerConfigAudit::SCHEMA, payload.fetch("schema"))
    assert_equal(1, payload.fetch("repos_with_drift"))
  end

  def test_clean_repo_exits_zero
    io = StringIO.new
    code = LabelerConfigAudit.run(
      ["--repo", "z-shell/clean", "--labels-file", LABELS_FILE],
      io: io,
      client: FixtureClient.new("z-shell/clean:.github/labeler.yml" => "area:ci:\n  - \".github/**\"\n")
    )
    assert_equal(0, code)
    assert(io.string.include?("Repos referencing non-canonical labels: 0"), io.string)
  end

  def test_missing_target_argument_is_a_usage_error
    assert_equal(2, LabelerConfigAudit.run([], io: StringIO.new, client: FixtureClient.new({})))
  end

  # A 404 means no config; any other API failure must surface rather than be
  # silently reported as a clean repository.
  def test_non_404_api_error_propagates
    files = { "z-shell/boom:.github/labeler.yml" => { message: "server error", status: 500 } }
    audit("z-shell/boom", files)
    raise "expected GitHubError"
  rescue LabelerConfigAudit::GitHubError => error
    assert_equal(500, error.status)
  end
end

tests = LabelerConfigAuditTest.new
methods = LabelerConfigAuditTest.instance_methods(false).grep(/^test_/).sort
failures = methods.filter_map do |method|
  tests.public_send(method)
  puts "PASS #{method}"
  nil
rescue StandardError => error
  warn "FAIL #{method}: #{error.message}"
  error
end

exit(failures.empty? ? 0 : 1)
