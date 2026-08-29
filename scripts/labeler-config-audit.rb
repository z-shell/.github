#!/usr/bin/env ruby
# frozen_string_literal: true

require "json"
require "open3"
require "optparse"
require "set"
require "yaml"

# Read-only audit that reports `.github/labeler.yml` label keys which are not in
# the canonical set in lib/labels.yml. Tracked on z-shell/.github#527.
#
# Why this needs its own check rather than showing up in labels-sync.rb: a
# dangling labeler reference never fails. `actions/labeler` applies labels
# through the issues API, which *creates* a label that does not exist instead of
# erroring. So a labeler.yml naming a deleted legacy label silently recreates it
# on the next matching pull request, and an org-wide label cleanup partially
# undoes itself with nothing in any log to show why. That is exactly how
# `enhancement ✨` returned to z-shell/zi after the #467 cleanup deleted it.
#
# Read-only by design: rewriting a labeler.yml changes which labels land on
# future pull requests in that repository, which is a per-repository editorial
# call rather than a uniform mechanical substitution. This script reports; the
# repository owner edits.
module LabelerConfigAudit
  SCHEMA = "z-shell/labeler-config-audit/v1"
  CONFIG_PATHS = [".github/labeler.yml", ".github/labeler.yaml"].freeze

  class GitHubError < StandardError
    attr_reader :status

    def initialize(message, status: nil)
      super(message)
      @status = status
    end
  end

  # Thin `gh api` wrapper, matching scripts/repo-settings-audit.rb's
  # GitHubClient shape so tests can inject a fixture stand-in instead of
  # shelling out.
  class GitHubClient
    def initialize(runner: nil)
      @runner = runner || lambda { |command| Open3.capture3(*command) }
    end

    # Returns nil for a missing file rather than raising. A repository without a
    # labeler config is not a finding, and must not be reported as one.
    def file(repo, path)
      command = ["gh", "api", "--method", "GET", "repos/#{repo}/contents/#{path}"]
      stdout, stderr, status = @runner.call(command)

      unless successful?(status)
        error = parse_error(stderr)
        return nil if error["status"] == 404

        raise GitHubError.new(error.fetch("message", "GitHub API request failed"), status: error["status"])
      end

      decode(stdout)
    end

    private

    def successful?(status)
      status.respond_to?(:success?) ? status.success? : status == true
    end

    def decode(body)
      parsed = JSON.parse(body)
      raise GitHubError, "contents response must be an object" unless parsed.is_a?(Hash)
      return nil unless parsed["content"]

      parsed.fetch("content").unpack1("m").force_encoding(Encoding::UTF_8)
    rescue JSON::ParserError => error
      raise GitHubError, "GitHub API returned invalid JSON: #{error.message}"
    end

    def parse_error(body)
      parsed = JSON.parse(body)
      return parsed.merge("status" => parsed["status"] || status_from(body)) if parsed.is_a?(Hash)

      { "message" => body.to_s.strip, "status" => status_from(body) }
    rescue JSON::ParserError
      { "message" => body.to_s.strip, "status" => status_from(body) }
    end

    def status_from(body)
      body.to_s[/HTTP\s+(\d{3})/, 1]&.to_i
    end
  end

  # The label keys of a labeler config.
  #
  # Both actions/labeler schemas are in use across the org: v4 maps a label to a
  # list of globs, v5 nests them under `any`/`all`. Only the top-level keys are
  # label names in either, so read those and ignore the values entirely.
  def self.label_keys(source)
    parsed = YAML.safe_load(source, aliases: true)
    raise GitHubError, "labeler config must be a mapping" unless parsed.is_a?(Hash)

    keys = parsed.keys
    raise GitHubError, "labeler config labels must be non-empty strings" unless keys.all? { |key| key.is_a?(String) && !key.empty? }

    keys
  rescue Psych::Exception => error
    raise GitHubError, "labeler config is not valid YAML: #{error.message}"
  end

  def self.canonical_labels(labels_file)
    data = YAML.safe_load_file(labels_file)
    Array(data.is_a?(Hash) ? data["labels"] : nil).filter_map { |entry| entry["name"] if entry.is_a?(Hash) }.to_set
  end

  def self.legacy_map(labels_file)
    data = YAML.safe_load_file(labels_file)
    map = data.is_a?(Hash) ? data["legacy_migrations"] : nil
    map.is_a?(Hash) ? map : {}
  end

  # One repository's findings. `config` is nil when the repository has no
  # labeler config at all, which is distinct from having one with no drift.
  def self.audit_repo(repo, client:, canonical:, legacy:)
    source = CONFIG_PATHS.filter_map { |path| client.file(repo, path) }.first
    return { "repo" => repo, "config" => nil, "unknown" => [], "summary" => { "unknown" => 0 } } if source.nil?

    unknown = label_keys(source).reject { |key| canonical.include?(key) }.map do |key|
      { "label" => key, "replacement" => legacy[key] }
    end

    {
      "repo" => repo,
      "config" => true,
      "unknown" => unknown,
      "summary" => { "unknown" => unknown.length }
    }
  end

  def self.render_markdown(results, io)
    drifted = results.select { |result| result.fetch("summary").fetch("unknown").positive? }

    io.puts "# Labeler config audit"
    io.puts
    io.puts "Repos scanned: #{results.length}"
    io.puts "Repos with a labeler config: #{results.count { |result| result['config'] }}"
    io.puts "Repos referencing non-canonical labels: #{drifted.length}"
    io.puts
    io.puts "A labeler key that is not in `lib/labels.yml` is recreated as a real"
    io.puts "label the next time the config matches a pull request. This audit is"
    io.puts "read-only; fixes belong in the owning repository."

    drifted.each do |result|
      io.puts
      io.puts "## #{result.fetch('repo')}"
      io.puts
      result.fetch("unknown").each do |entry|
        replacement = entry["replacement"]
        suffix = replacement ? " -> `#{replacement}`" : " (no canonical replacement recorded)"
        io.puts "- `#{entry.fetch('label')}`#{suffix}"
      end
    end
  end

  def self.run(argv, io: $stdout, client: nil)
    options = {
      labels_file: File.join(File.expand_path("..", __dir__), "lib", "labels.yml"),
      org: "z-shell",
      repos: [],
      all_repos: false,
      json: false
    }

    parser = OptionParser.new do |opts|
      opts.banner = "Usage: #{$PROGRAM_NAME} [options]"
      opts.on("--labels-file PATH", "Canonical labels file") { |value| options[:labels_file] = value }
      opts.on("--org ORG", "Organization for --all-repos") { |value| options[:org] = value }
      opts.on("--repo OWNER/REPO", "Repository to audit; may be repeated") { |value| options[:repos] << value }
      opts.on("--all-repos", "Audit every repository in --org") { options[:all_repos] = true }
      opts.on("--json", "Emit JSON instead of Markdown") { options[:json] = true }
      opts.on("-h", "--help", "Show this help") do
        io.puts opts
        return 0
      end
    end
    parser.parse!(argv)

    if !options[:all_repos] && options[:repos].empty?
      warn parser
      warn "\nerror: pass at least one --repo OWNER/REPO or --all-repos"
      return 2
    end

    if options[:all_repos] && !options[:repos].empty?
      warn parser
      warn "\nerror: use either --all-repos or --repo values, not both"
      return 2
    end

    client ||= GitHubClient.new
    canonical = canonical_labels(options[:labels_file])
    legacy = legacy_map(options[:labels_file])

    repos = options[:repos]
    if options[:all_repos]
      stdout, _stderr, _status = Open3.capture3("gh", "repo", "list", options[:org], "--limit", "1000",
                                                "--json", "nameWithOwner")
      repos = JSON.parse(stdout).map { |entry| entry.fetch("nameWithOwner") }
    end

    results = repos.sort.map { |repo| audit_repo(repo, client: client, canonical: canonical, legacy: legacy) }
    drifted = results.count { |result| result.fetch("summary").fetch("unknown").positive? }

    if options[:json]
      io.puts JSON.pretty_generate(
        "schema" => SCHEMA,
        "labels_file" => options[:labels_file],
        "repos_scanned" => results.length,
        "repos_with_drift" => drifted,
        "results" => results
      )
    else
      render_markdown(results, io)
    end

    drifted.zero? ? 0 : 1
  end
end

exit(LabelerConfigAudit.run(ARGV)) if $PROGRAM_NAME == __FILE__
