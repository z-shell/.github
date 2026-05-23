#!/usr/bin/env ruby
# frozen_string_literal: true

# Audit z-shell label synchronization drift, with a tightly gated apply-mode
# pilot for canonical label create/update operations.
#
# Default behavior is intentionally read-only: it uses only GET-style `gh api`
# calls and never creates, updates, deletes, or migrates labels unless both
# `--apply` and `--confirm-apply` are passed for explicit `--repo` targets.

require "json"
require "open3"
require "optparse"
require "uri"
require "yaml"

ROOT = File.expand_path("..", __dir__)
DEFAULT_LABELS_FILE = File.join(ROOT, "lib", "labels.yml")

# Temporary pilot allowlist. Keep this intentionally tiny until #411 has one
# reviewed create/update-only pilot result. Use --allow-non-pilot-repo only
# after maintainer approval.
PILOT_APPLY_REPOS = [
  "z-shell/.github"
].freeze

Options = Struct.new(
  :labels_file,
  :org,
  :repos,
  :all_repos,
  :json,
  :include_clean,
  :apply,
  :confirm_apply,
  :allow_non_pilot_repo,
  keyword_init: true
)

options = Options.new(
  labels_file: DEFAULT_LABELS_FILE,
  org: "z-shell",
  repos: [],
  all_repos: false,
  json: false,
  include_clean: false,
  apply: false,
  confirm_apply: false,
  allow_non_pilot_repo: false
)

parser = OptionParser.new do |opts|
  opts.banner = "Usage: #{$PROGRAM_NAME} [options]"

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

  opts.on("--apply", "Preview canonical label create/update operations for explicit repos") do
    options.apply = true
  end

  opts.on("--confirm-apply", "Actually apply --apply canonical label create/update operations") do
    options.confirm_apply = true
  end

  opts.on("--allow-non-pilot-repo", "Allow confirmed apply outside the temporary pilot allowlist") do
    options.allow_non_pilot_repo = true
  end

  opts.on("-h", "--help", "Show this help") do
    puts opts
    exit 0
  end
end

begin
  parser.parse!
rescue OptionParser::ParseError => e
  warn parser
  warn "\nerror: #{e.message}"
  exit 2
end

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

if options.confirm_apply && !options.apply
  warn parser
  warn "\nerror: --confirm-apply requires --apply"
  exit 2
end

if options.apply && options.all_repos
  warn parser
  warn "\nerror: --apply is only allowed with explicit --repo values during the pilot"
  exit 2
end

if options.apply && options.confirm_apply && !options.allow_non_pilot_repo
  outside_pilot = options.repos.reject { |repo| PILOT_APPLY_REPOS.include?(repo) }
  unless outside_pilot.empty?
    warn "error: apply pilot is limited to: #{PILOT_APPLY_REPOS.join(', ')}"
    warn "rerun with --allow-non-pilot-repo only after maintainer approval"
    exit 2
  end
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
    "gh", "api", path, "--paginate", "--jq", ".[]"
  )
  unless status.success?
    raise "gh api #{path} failed: #{stderr.strip.empty? ? stdout.strip : stderr.strip}"
  end

  stdout.lines.reject { |line| line.strip.empty? }.map { |line| JSON.parse(line) }
end

def gh_api_mutation(*args)
  stdout, stderr, status = Open3.capture3("gh", "api", *args)
  unless status.success?
    raise "gh api #{args.join(' ')} failed: #{stderr.strip.empty? ? stdout.strip : stderr.strip}"
  end
  stdout.strip.empty? ? {} : JSON.parse(stdout)
end

def label_path_segment(name)
  URI.encode_www_form_component(name).gsub("+", "%20")
end

def create_label(owner_repo, label)
  gh_api_mutation(
    "repos/#{owner_repo}/labels",
    "--method", "POST",
    "-f", "name=#{label.fetch('name')}",
    "-f", "color=#{label.fetch('color')}",
    "-f", "description=#{label.fetch('description')}"
  )
end

def update_label(owner_repo, label)
  gh_api_mutation(
    "repos/#{owner_repo}/labels/#{label_path_segment(label.fetch('name'))}",
    "--method", "PATCH",
    "-f", "new_name=#{label.fetch('name')}",
    "-f", "color=#{label.fetch('color')}",
    "-f", "description=#{label.fetch('description')}"
  )
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

def planned_label_operations(result, canonical)
  creates = result.fetch("missing").map { |name| canonical.fetch(name) }
  updates = result.fetch("updates").map { |item| canonical.fetch(item.fetch("name")) }

  {
    "would_create" => creates,
    "would_update" => updates,
    "skipped_legacy" => result.fetch("legacy_present").map { |item| item.fetch("legacy") },
    "skipped_unknown" => result.fetch("unknown")
  }
end

def apply_label_operations(owner_repo, operations)
  result = {
    "created" => [],
    "updated" => [],
    "skipped_legacy" => operations.fetch("skipped_legacy"),
    "skipped_unknown" => operations.fetch("skipped_unknown"),
    "errors" => []
  }

  operations.fetch("would_create").each do |label|
    begin
      create_label(owner_repo, label)
      result.fetch("created") << label.fetch("name")
    rescue StandardError => e
      result.fetch("errors") << {
        "operation" => "create",
        "label" => label.fetch("name"),
        "message" => e.message
      }
      return result
    end
  end

  operations.fetch("would_update").each do |label|
    begin
      update_label(owner_repo, label)
      result.fetch("updated") << label.fetch("name")
    rescue StandardError => e
      result.fetch("errors") << {
        "operation" => "update",
        "label" => label.fetch("name"),
        "message" => e.message
      }
      return result
    end
  end

  result
end

def clean?(result)
  result.fetch("summary").values.all?(&:zero?)
end

def print_label_list(title, labels)
  return if labels.empty?

  puts title
  labels.each do |label|
    if label.is_a?(Hash) && label.key?("operation")
      puts "- [#{label.fetch('operation')}] #{label.fetch('label')}: #{label.fetch('message')}"
    else
      name = label.is_a?(Hash) ? label.fetch("name") : label
      puts "- #{name}"
    end
  end
  puts
end

canonical, legacy_migrations, sync_policy = canonical_label_map(options.labels_file)
repos = options.all_repos ? repo_list(options.org) : options.repos
results = repos.sort.map { |repo| diff_repo(repo, canonical, legacy_migrations) }

if options.apply
  results.each do |result|
    result["operations"] = planned_label_operations(result, canonical)
  end
end

apply_failed = false
if options.apply && options.confirm_apply
  results.each do |result|
    result["applied"] = apply_label_operations(result.fetch("repo"), result.fetch("operations"))
    apply_failed ||= !result.fetch("applied").fetch("errors").empty?
  end
end

payload = {
  "mode" => options.apply ? (options.confirm_apply ? "apply" : "apply-preview") : "dry-run",
  "confirmed" => options.confirm_apply,
  "labels_file" => options.labels_file,
  "canonical_labels" => canonical.length,
  "legacy_migrations" => legacy_migrations.length,
  "sync_policy" => sync_policy,
  "pilot_apply_repos" => PILOT_APPLY_REPOS,
  "repos_scanned" => results.length,
  "repos_with_drift" => results.count { |result| !clean?(result) },
  "results" => results
}

if options.json
  puts JSON.pretty_generate(payload)
  exit(apply_failed ? 1 : 0)
end

exit 1 if apply_failed

heading = options.apply ? "# Label sync apply preview" : "# Label sync dry-run"
heading = "# Label sync apply result" if options.apply && options.confirm_apply
puts heading
puts
puts "Mode: #{payload.fetch('mode')}"
puts "Labels file: `#{options.labels_file}`"
puts "Canonical labels: #{canonical.length}"
puts "Legacy migrations: #{legacy_migrations.length}"
puts "Repos scanned: #{results.length}"
puts "Repos with drift: #{payload.fetch('repos_with_drift')}"
puts

if options.apply && options.confirm_apply
  puts "Confirmed apply mode: canonical labels may have been created or updated."
elsif options.apply
  puts "Apply preview only. Pass --confirm-apply to create/update canonical labels."
else
  puts "This is a read-only dry run. No labels or issues were changed."
end
puts "Legacy and unknown labels are skipped/preserved; no labels are deleted."
puts

puts "## Sync policy"
puts
sync_policy.each do |key, value|
  puts "- #{key}: #{value}"
end
puts

if options.apply
  puts "## Apply pilot guardrails"
  puts
  puts "- org-wide apply is disabled"
  puts "- confirmed apply requires explicit --repo values"
  puts "- pilot allowlist: #{PILOT_APPLY_REPOS.join(', ')}"
  puts "- use --allow-non-pilot-repo only after maintainer approval"
  puts
end

results.each do |result|
  next if clean?(result) && !options.include_clean && !options.apply

  puts "## #{result.fetch('repo')}"
  puts
  if clean?(result)
    puts "Clean: no missing, mismatched, legacy, or unknown labels."
    puts
  end

  if options.apply
    operations = result.fetch("operations")
    print_label_list("### Would create", operations.fetch("would_create"))
    print_label_list("### Would update", operations.fetch("would_update"))
    print_label_list("### Skipped legacy labels", operations.fetch("skipped_legacy"))
    print_label_list("### Skipped unknown local labels", operations.fetch("skipped_unknown"))

    if result.key?("applied")
      applied = result.fetch("applied")
      print_label_list("### Created", applied.fetch("created"))
      print_label_list("### Updated", applied.fetch("updated"))
      print_label_list("### Apply errors", applied.fetch("errors"))
    end
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
