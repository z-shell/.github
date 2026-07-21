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
  :migrate_legacy,
  :confirm_migrate_legacy,
  :delete_unused_legacy,
  :confirm_delete_unused_legacy,
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
  allow_non_pilot_repo: false,
  migrate_legacy: false,
  confirm_migrate_legacy: false,
  delete_unused_legacy: false,
  confirm_delete_unused_legacy: false
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

  opts.on("--migrate-legacy", "Preview migrating in-use legacy labels onto their canonical replacement") do
    options.migrate_legacy = true
  end

  opts.on("--confirm-migrate-legacy", "Actually relabel items and remove the migrated legacy labels") do
    options.confirm_migrate_legacy = true
  end

  opts.on("--delete-unused-legacy", "Preview deleting legacy labels that are attached to nothing") do
    options.delete_unused_legacy = true
  end

  opts.on("--confirm-delete-unused-legacy", "Actually delete the unused legacy labels") do
    options.confirm_delete_unused_legacy = true
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

# Destructive modes reuse the apply guardrails: a confirm flag is inert without
# its preview flag, neither mode may fan out across the whole org, and a
# confirmed run stays inside the pilot allowlist unless explicitly waived.
DESTRUCTIVE_MODES = {
  "migrate-legacy" => %i[migrate_legacy confirm_migrate_legacy],
  "delete-unused-legacy" => %i[delete_unused_legacy confirm_delete_unused_legacy]
}.freeze

DESTRUCTIVE_MODES.each do |name, (preview_flag, confirm_flag)|
  preview = options.public_send(preview_flag)
  confirm = options.public_send(confirm_flag)

  if confirm && !preview
    warn parser
    warn "\nerror: --confirm-#{name} requires --#{name}"
    exit 2
  end

  if preview && options.all_repos
    warn parser
    warn "\nerror: --#{name} is only allowed with explicit --repo values"
    exit 2
  end

  next unless preview && confirm && !options.allow_non_pilot_repo

  outside_pilot = options.repos.reject { |repo| PILOT_APPLY_REPOS.include?(repo) }
  next if outside_pilot.empty?

  warn "error: --#{name} pilot is limited to: #{PILOT_APPLY_REPOS.join(', ')}"
  warn "rerun with --allow-non-pilot-repo only after maintainer approval"
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

def delete_label(owner_repo, name)
  gh_api_mutation(
    "repos/#{owner_repo}/labels/#{label_path_segment(name)}",
    "--method", "DELETE"
  )
end

def add_label_to_item(owner_repo, number, name)
  gh_api_mutation(
    "repos/#{owner_repo}/issues/#{number}/labels",
    "--method", "POST",
    "-f", "labels[]=#{name}"
  )
end

# Every issue and pull request in any state, with the labels each one carries.
# Closed items count: deleting a label strips it from them too.
def repo_items(owner_repo)
  gh_paginated_array("repos/#{owner_repo}/issues?state=all&per_page=100").map do |item|
    {
      "number" => item.fetch("number"),
      "labels" => (item["labels"] || []).map { |label| label.is_a?(Hash) ? label.fetch("name") : label }
    }
  end
end

# name => number of items carrying it. Absent names are unused.
def label_usage(items)
  items.each_with_object(Hash.new(0)) do |item, counts|
    item.fetch("labels").each { |name| counts[name] += 1 }
  end
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

  updates = canonical.each_with_object([]) do |(name, desired), items|
    current = live_by_name[name]
    next unless current

    changes = {}
    if current.fetch("color") != desired.fetch("color")
      changes["color"] = { "current" => current.fetch("color"), "desired" => desired.fetch("color") }
    end
    if current.fetch("description") != desired.fetch("description")
      changes["description"] = { "current" => current.fetch("description"), "desired" => desired.fetch("description") }
    end
    items << { "name" => name, "changes" => changes } unless changes.empty?
  end

  legacy_present = legacy_migrations.each_with_object([]) do |(legacy, replacement), items|
    next unless live_by_name.key?(legacy)

    items << { "legacy" => legacy, "replacement" => replacement }
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

# Plan the destructive work for one repo. Reads live usage rather than any
# cached audit, so a label that gained an item since the last scan is seen as
# in use. Unknown labels are never planned for deletion.
def planned_legacy_operations(result, canonical, items)
  usage = label_usage(items)

  migrations = []
  deletions = []
  blocked = []

  result.fetch("legacy_present").each do |entry|
    legacy = entry.fetch("legacy")
    replacement = entry.fetch("replacement")
    count = usage[legacy]

    unless canonical.key?(replacement)
      blocked << {
        "legacy" => legacy,
        "reason" => "replacement #{replacement} is not a canonical label"
      }
      next
    end

    if count.zero?
      deletions << { "legacy" => legacy, "items" => 0 }
      next
    end

    carrying = items.select { |item| item.fetch("labels").include?(legacy) }
                    .map { |item| item.fetch("number") }
                    .sort

    migrations << {
      "legacy" => legacy,
      "replacement" => replacement,
      "items" => carrying,
      "count" => carrying.length
    }
  end

  {
    "would_migrate" => migrations.sort_by { |item| item.fetch("legacy") },
    "would_delete_unused" => deletions.sort_by { |item| item.fetch("legacy") },
    "blocked" => blocked.sort_by { |item| item.fetch("legacy") },
    "protected_unknown" => result.fetch("unknown")
  }
end

# Order is load-bearing. The canonical label goes onto every carrying item and is
# verified to have landed before the legacy label is removed; deleting first
# would strip the association with nothing to replace it.
def migrate_legacy_labels(owner_repo, operations)
  result = { "relabelled" => [], "removed" => [], "errors" => [] }

  operations.fetch("would_migrate").each do |migration|
    legacy = migration.fetch("legacy")
    replacement = migration.fetch("replacement")
    relabelled = []

    begin
      migration.fetch("items").each do |number|
        add_label_to_item(owner_repo, number, replacement)
        relabelled << number
      end

      still_missing = repo_items(owner_repo).select do |item|
        migration.fetch("items").include?(item.fetch("number")) &&
          !item.fetch("labels").include?(replacement)
      end

      unless still_missing.empty?
        raise "#{replacement} did not land on items #{still_missing.map { |i| i.fetch('number') }.join(', ')}"
      end

      delete_label(owner_repo, legacy)
      result.fetch("removed") << legacy
      result.fetch("relabelled") << { "legacy" => legacy, "replacement" => replacement, "items" => relabelled }
    rescue StandardError => e
      result.fetch("errors") << {
        "operation" => "migrate",
        "label" => legacy,
        "message" => e.message
      }
      return result
    end
  end

  result
end

def delete_unused_legacy_labels(owner_repo, operations)
  result = { "deleted" => [], "errors" => [] }

  operations.fetch("would_delete_unused").each do |entry|
    legacy = entry.fetch("legacy")
    begin
      delete_label(owner_repo, legacy)
      result.fetch("deleted") << legacy
    rescue StandardError => e
      result.fetch("errors") << {
        "operation" => "delete",
        "label" => legacy,
        "message" => e.message
      }
      return result
    end
  end

  result
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
    name = label.is_a?(Hash) ? label.fetch("name") : label
    puts "- #{name}"
  end
  puts
end

def print_apply_errors(errors)
  return if errors.empty?

  puts "### Apply errors"
  errors.each do |error|
    puts "- #{error.fetch('operation')} #{error.fetch('label')}: #{error.fetch('message')}"
  end
  puts
end

canonical, legacy_migrations, sync_policy = canonical_label_map(options.labels_file)

# sync_policy is the source of truth for what the destructive modes may do. The
# script only ever implements delete-when-unused, so a false value for that key
# disables the mode outright rather than widening it.
if options.delete_unused_legacy && !sync_policy.fetch("delete_legacy_labels_only_when_unused", false)
  warn "error: sync_policy.delete_legacy_labels_only_when_unused is not enabled in #{options.labels_file}"
  warn "the delete mode implements unused-only deletion and refuses to run without it"
  exit 2
end

if options.migrate_legacy && !sync_policy.fetch("preserve_labels_on_open_items_before_removal", false)
  warn "error: sync_policy.preserve_labels_on_open_items_before_removal is not enabled in #{options.labels_file}"
  warn "migration exists to preserve labelling before removal and refuses to run without it"
  exit 2
end

repos = options.all_repos ? repo_list(options.org) : options.repos
results = repos.sort.map { |repo| diff_repo(repo, canonical, legacy_migrations) }

if options.apply
  results.each do |result|
    result["operations"] = planned_label_operations(result, canonical)
  end
end

legacy_mode = options.migrate_legacy || options.delete_unused_legacy
if legacy_mode
  results.each do |result|
    items = repo_items(result.fetch("repo"))
    result["legacy_operations"] = planned_legacy_operations(result, canonical, items)
  end
end

apply_failed = false
if options.apply && options.confirm_apply
  results.each do |result|
    result["applied"] = apply_label_operations(result.fetch("repo"), result.fetch("operations"))
    apply_failed ||= !result.fetch("applied").fetch("errors").empty?
  end
end

legacy_failed = false
if options.migrate_legacy && options.confirm_migrate_legacy
  results.each do |result|
    outcome = migrate_legacy_labels(result.fetch("repo"), result.fetch("legacy_operations"))
    result["migrated"] = outcome
    legacy_failed ||= !outcome.fetch("errors").empty?
  end
end

if options.delete_unused_legacy && options.confirm_delete_unused_legacy
  results.each do |result|
    outcome = delete_unused_legacy_labels(result.fetch("repo"), result.fetch("legacy_operations"))
    result["deleted"] = outcome
    legacy_failed ||= !outcome.fetch("errors").empty?
  end
end

mode =
  if options.migrate_legacy
    options.confirm_migrate_legacy ? "migrate" : "migrate-preview"
  elsif options.delete_unused_legacy
    options.confirm_delete_unused_legacy ? "delete" : "delete-preview"
  elsif options.apply
    options.confirm_apply ? "apply" : "apply-preview"
  else
    "dry-run"
  end

payload = {
  "mode" => mode,
  "confirmed" => options.confirm_apply || options.confirm_migrate_legacy || options.confirm_delete_unused_legacy,
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
  exit(apply_failed || legacy_failed ? 1 : 0)
end

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
if legacy_mode
  puts "Unknown labels are never deleted. Legacy labels are removed only after " \
       "their canonical replacement is verified on every carrying item, or when " \
       "they are attached to nothing."
else
  puts "Legacy and unknown labels are skipped/preserved; no labels are deleted."
end
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
      print_apply_errors(applied.fetch("errors"))
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

  next unless legacy_mode

  legacy_operations = result.fetch("legacy_operations")

  unless legacy_operations.fetch("would_migrate").empty?
    puts "### Would migrate (relabel items, then remove legacy)"
    legacy_operations.fetch("would_migrate").each do |item|
      puts "- #{item.fetch('legacy')} -> #{item.fetch('replacement')} (#{item.fetch('count')} item(s))"
    end
    puts
  end

  unless legacy_operations.fetch("would_delete_unused").empty?
    puts "### Would delete (unused legacy labels)"
    legacy_operations.fetch("would_delete_unused").each { |item| puts "- #{item.fetch('legacy')}" }
    puts
  end

  unless legacy_operations.fetch("blocked").empty?
    puts "### Blocked"
    legacy_operations.fetch("blocked").each do |item|
      puts "- #{item.fetch('legacy')}: #{item.fetch('reason')}"
    end
    puts
  end

  print_apply_errors(result.dig("migrated", "errors") || [])
  print_apply_errors(result.dig("deleted", "errors") || [])
end

exit(apply_failed || legacy_failed ? 1 : 0)
