#!/usr/bin/env ruby
# frozen_string_literal: true

# Dry-run z-shell label synchronization audit.
#
# Reads lib/labels.yml and compares it with one or more GitHub repositories.
# This script is intentionally read-only: it uses only GET-style `gh api` calls
# and never creates, updates, deletes, or migrates labels.

require "json"
require "open3"
require "optparse"
require "yaml"

ROOT = File.expand_path("..", __dir__)
DEFAULT_LABELS_FILE = File.join(ROOT, "lib", "labels.yml")

Options = Struct.new(
  :labels_file,
  :org,
  :repos,
  :all_repos,
  :json,
  :include_clean,
  keyword_init: true
)

options = Options.new(
  labels_file: DEFAULT_LABELS_FILE,
  org: "z-shell",
  repos: [],
  all_repos: false,
  json: false,
  include_clean: false
)

parser = OptionParser.new do |opts|
  opts.banner = "Usage: scripts/labels-dry-run.rb [options]"

  opts.on("--labels-file PATH", "Canonical labels file (default: lib/labels.yml)") do |path|
    options.labels_file = path
  end

  opts.on("--org ORG", "GitHub organization for --all-repos (default: z-shell)") do |org|
    options.org = org
  end

  opts.on("--repo OWNER/REPO", "Repository to audit; may be repeated") do |repo|
    options.repos << repo
  end

  opts.on("--all-repos", "Audit every repository in --org") do
    options.all_repos = true
  end

  opts.on("--json", "Emit JSON instead of Markdown") do
    options.json = true
  end

  opts.on("--include-clean", "Include clean repos in Markdown output") do
    options.include_clean = true
  end

  opts.on("-h", "--help", "Show this help") do
    puts opts
    exit 0
  end
end

parser.parse!

if options.all_repos && !options.repos.empty?
  warn parser
  warn "\nerror: use either --all-repos or one or more --repo values, not both"
  exit 2
end

if !options.all_repos && options.repos.empty?
  warn parser
  warn "\nerror: pass at least one --repo OWNER/REPO or --all-repos"
  exit 2
end

def gh_json(*args)
  stdout, stderr, status = Open3.capture3("gh", *args)
  unless status.success?
    raise "gh #{args.join(' ')} failed: #{stderr.strip.empty? ? stdout.strip : stderr.strip}"
  end
  JSON.parse(stdout.empty? ? "[]" : stdout)
end

def gh_paginated_array(path)
  stdout, stderr, status = Open3.capture3(
    "gh", "api", path, "--paginate", "--template", "{{range .}}{{json .}}{{\"\\n\"}}{{end}}"
  )
  unless status.success?
    raise "gh api #{path} failed: #{stderr.strip.empty? ? stdout.strip : stderr.strip}"
  end

  stdout.lines.reject { |line| line.strip.empty? }.map { |line| JSON.parse(line) }
end

def repo_list(org)
  gh_json("repo", "list", org, "--limit", "1000", "--json", "nameWithOwner").map { |repo| repo.fetch("nameWithOwner") }
end

def repo_labels(owner_repo)
  gh_paginated_array("repos/#{owner_repo}/labels?per_page=100").map do |label|
    {
      "name" => label.fetch("name"),
      "color" => label.fetch("color").downcase,
      "description" => (label["description"] || "")
    }
  end
end

def canonical_label_map(labels_file)
  data = YAML.safe_load(
    File.read(labels_file),
    permitted_classes: [],
    permitted_symbols: [],
    aliases: false
  )
  raise "labels file must contain a mapping" unless data.is_a?(Hash)

  labels = data.fetch("labels")
  raise "labels must be a list" unless labels.is_a?(Array)

  label_names = labels.map { |label| label.fetch("name") }
  duplicate_names = label_names.select { |name| label_names.count(name) > 1 }.uniq
  raise "duplicate canonical labels: #{duplicate_names.join(', ')}" unless duplicate_names.empty?

  [
    labels.to_h do |label|
      [
        label.fetch("name"),
        {
          "name" => label.fetch("name"),
          "color" => label.fetch("color").to_s.downcase,
          "description" => (label["description"] || "")
        }
      ]
    end,
    data.fetch("legacy_migrations", {}) || {},
    data.fetch("sync_policy", {}) || {}
  ]
end

def diff_repo(owner_repo, canonical, legacy_migrations)
  live = repo_labels(owner_repo)
  live_by_name = live.to_h { |label| [label.fetch("name"), label] }

  missing = canonical.keys.reject { |name| live_by_name.key?(name) }

  updates = canonical.filter_map do |name, desired|
    current = live_by_name[name]
    next unless current

    changes = {}
    if current.fetch("color") != desired.fetch("color")
      changes["color"] = { "current" => current.fetch("color"), "desired" => desired.fetch("color") }
    end
    if current.fetch("description") != desired.fetch("description")
      changes["description"] = { "current" => current.fetch("description"), "desired" => desired.fetch("description") }
    end
    changes.empty? ? nil : { "name" => name, "changes" => changes }
  end

  legacy_present = legacy_migrations.filter_map do |legacy, replacement|
    next unless live_by_name.key?(legacy)

    { "legacy" => legacy, "replacement" => replacement }
  end

  unknown = live_by_name.keys.reject do |name|
    canonical.key?(name) || legacy_migrations.key?(name)
  end.sort

  {
    "repo" => owner_repo,
    "missing" => missing.sort,
    "updates" => updates.sort_by { |item| item.fetch("name") },
    "legacy_present" => legacy_present.sort_by { |item| item.fetch("legacy") },
    "unknown" => unknown,
    "summary" => {
      "missing" => missing.length,
      "updates" => updates.length,
      "legacy_present" => legacy_present.length,
      "unknown" => unknown.length
    }
  }
end

def clean?(result)
  result.fetch("summary").values.all?(&:zero?)
end

canonical, legacy_migrations, sync_policy = canonical_label_map(options.labels_file)
repos = options.all_repos ? repo_list(options.org) : options.repos
results = repos.sort.map { |repo| diff_repo(repo, canonical, legacy_migrations) }

payload = {
  "labels_file" => options.labels_file,
  "canonical_labels" => canonical.length,
  "legacy_migrations" => legacy_migrations.length,
  "sync_policy" => sync_policy,
  "repos_scanned" => results.length,
  "repos_with_drift" => results.count { |result| !clean?(result) },
  "results" => results
}

if options.json
  puts JSON.pretty_generate(payload)
  exit 0
end

puts "# Label sync dry-run"
puts
puts "Labels file: `#{options.labels_file}`"
puts "Canonical labels: #{canonical.length}"
puts "Legacy migrations: #{legacy_migrations.length}"
puts "Repos scanned: #{results.length}"
puts "Repos with drift: #{payload.fetch('repos_with_drift')}"
puts
puts "This is a read-only dry run. No labels or issues were changed."
puts
puts "## Sync policy"
puts
sync_policy.each do |key, value|
  puts "- #{key}: #{value}"
end
puts

results.each do |result|
  next if clean?(result) && !options.include_clean

  puts "## #{result.fetch('repo')}"
  puts
  if clean?(result)
    puts "Clean: no missing, mismatched, legacy, or unknown labels."
    puts
    next
  end

  unless result.fetch("missing").empty?
    puts "### Would create"
    result.fetch("missing").each { |name| puts "- #{name}" }
    puts
  end

  unless result.fetch("updates").empty?
    puts "### Would update"
    result.fetch("updates").each do |item|
      puts "- #{item.fetch('name')}"
      item.fetch("changes").each do |field, change|
        puts "  - #{field}: `#{change.fetch('current')}` -> `#{change.fetch('desired')}`"
      end
    end
    puts
  end

  unless result.fetch("legacy_present").empty?
    puts "### Legacy labels present"
    result.fetch("legacy_present").each do |item|
      puts "- #{item.fetch('legacy')} -> #{item.fetch('replacement')}"
    end
    puts
  end

  unless result.fetch("unknown").empty?
    puts "### Unknown local labels (preserve; review manually)"
    result.fetch("unknown").each { |name| puts "- #{name}" }
    puts
  end
end
