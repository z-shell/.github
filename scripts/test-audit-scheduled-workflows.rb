#!/usr/bin/env ruby
# frozen_string_literal: true

require "json"
require "stringio"
require "tmpdir"
require "yaml"

require_relative "audit-scheduled-workflows"

class ScheduledWorkflowAuditTest
  FIXTURES = File.expand_path("fixtures/scheduled-workflows", __dir__)

  def fixture(name)
    YAML.safe_load_file(File.join(FIXTURES, "#{name}.yml"), aliases: false)
  end

  def assert_equal(expected, actual)
    raise "expected #{expected.inspect}, got #{actual.inspect}" unless expected == actual
  end

  def assert(value)
    raise "expected truthy value" unless value
  end

  def refute(value)
    raise "expected falsey value" if value
  end

  def assert_includes(haystack, needle)
    raise "expected #{haystack.inspect} to include #{needle.inspect}" unless haystack.include?(needle)
  end

  def refute_includes(haystack, needle)
    raise "expected #{haystack.inspect} not to include #{needle.inspect}" if haystack.include?(needle)
  end

  def assert_match(pattern, actual)
    raise "expected #{actual.inspect} to match #{pattern.inspect}" unless pattern.match?(actual)
  end

  def assert_raises(error_class)
    yield
    raise "expected #{error_class}"
  rescue error_class => error
    error
  end

  def parse(name)
    data = fixture(name)
    ScheduledWorkflowAudit::WorkflowParser.new.parse(
      repository: data.fetch("repository"),
      metadata: data.fetch("workflow"),
      content: data.fetch("content")
    )
  end

  def test_parser_returns_the_versioned_record_shape
    assert_equal(
      {
        "schema" => "z-shell/scheduled-workflow-audit/v1",
        "repository" => "example/utc-demo",
        "visibility" => "public",
        "default_branch" => "main",
        "path" => ".github/workflows/check.yml",
        "name" => "Check",
        "state" => "active",
        "schedules" => [{ "cron" => "17 9 * * 6", "timezone" => "UTC" }],
        "workflow_dispatch" => true,
        "permissions_locations" => ["workflow"],
        "concurrency_locations" => ["workflow"],
        "reusable_calls" => ["example/reusable/.github/workflows/lint.yml@main"],
        "errors" => []
      },
      parse("active-utc")
    )
  end

  def test_parser_preserves_an_explicit_iana_timezone_and_multiple_crons
    assert_equal [{ "cron" => "0 8 * * 1-5", "timezone" => "Europe/London" }], parse("active-iana-timezone").fetch("schedules")
    assert_equal 2, parse("multiple-cron").fetch("schedules").length
  end

  def test_parser_defaults_invalid_timezones_to_utc
    data = fixture("active-utc")
    data["content"] = <<~YAML
      on:
        schedule:
          - cron: "17 9 * * 6"
            timezone: ""
          - cron: "18 9 * * 6"
            timezone: 42
      jobs: {}
    YAML

    record = ScheduledWorkflowAudit::WorkflowParser.new.parse(
      repository: data.fetch("repository"),
      metadata: data.fetch("workflow"),
      content: data.fetch("content")
    )

    assert_equal ["UTC", "UTC"], record.fetch("schedules").map { |schedule| schedule.fetch("timezone") }
  end

  def test_parser_treats_a_comment_only_workflow_as_unscheduled
    assert_equal [], parse("comment-only-workflow").fetch("schedules")
  end

  def test_parser_rejects_a_non_mapping_workflow_document
    data = fixture("comment-only-workflow")
    error = assert_raises(ArgumentError) do
      ScheduledWorkflowAudit::WorkflowParser.new.parse(
        repository: data.fetch("repository"), metadata: data.fetch("workflow"), content: "[]\n"
      )
    end

    assert_match(/mapping/, error.message)
  end

  def test_parser_finds_job_and_workflow_controls
    assert_equal ["job"], parse("job-level-controls").fetch("permissions_locations")
    assert_equal ["job"], parse("job-level-controls").fetch("concurrency_locations")
    assert_equal ["workflow"], parse("top-level-controls").fetch("permissions_locations")
    assert_equal ["workflow"], parse("top-level-controls").fetch("concurrency_locations")
    assert_equal ["example/platform/.github/workflows/reusable.yml@v1"], parse("reusable-workflow-caller").fetch("reusable_calls")
  end

  def test_inventory_includes_disabled_workflows_unless_active_only_is_selected
    inventory = ScheduledWorkflowAudit::Inventory.new(
      client: FixtureClient.new([fixture("active-utc"), fixture("disabled-inactivity")]),
      org: "example"
    )

    assert_equal ["example/inactive-demo", "example/utc-demo"], inventory.run.map { |record| record.fetch("repository") }
    assert_equal 1, inventory.run(active_only: true).length
  end

  def test_markdown_hides_private_repository_names
    rendered = ScheduledWorkflowAudit::Renderer.new.markdown(
      [parse("active-utc"), parse("private-redaction")],
      public_only: false
    )

    assert_includes rendered, "example/utc-demo"
    refute_includes rendered, "example/hidden-repository"
  end

  def test_markdown_escapes_table_delimiters_and_newlines
    record = parse("active-utc")
    record["repository"] = "example/pipe|repo\ncontinued"
    record["name"] = "Check|Now\nLater"
    record["state"] = "active|queued\nstate"
    record["schedules"] = [{ "cron" => "17|18\n19", "timezone" => "UTC|Local\nZone" }]

    rendered = ScheduledWorkflowAudit::Renderer.new.markdown([record], public_only: false)

    assert_includes rendered, "example/pipe\\|repo<br>continued"
    assert_includes rendered, "Check\\|Now<br>Later"
    assert_includes rendered, "active\\|queued<br>state"
    assert_includes rendered, "17\\|18<br>19 (UTC\\|Local<br>Zone)"
  end

  def test_repository_scope_does_not_require_an_organization
    stdout = StringIO.new
    stderr = StringIO.new
    status = ScheduledWorkflowAudit::CLI.run(
      ["--repo", "example/utc-demo", "--format", "markdown"],
      client: FixtureClient.new([fixture("active-utc")]), stdout: stdout, stderr: stderr
    )

    assert_equal 0, status
    assert_equal "", stderr.string
    assert_includes stdout.string, "example/utc-demo"
  end

  def test_private_json_requires_a_private_output_file
    stdout = StringIO.new
    stderr = StringIO.new

    status = ScheduledWorkflowAudit::CLI.run(
      ["--org", "example", "--format", "json"],
      client: FixtureClient.new([fixture("private-redaction")]), stdout: stdout, stderr: stderr
    )

    assert_equal 2, status
    assert_match(/--output FILE/, stderr.string)
  end

  def test_private_target_without_a_scheduled_workflow_still_requires_an_output_file
    stderr = StringIO.new
    status = ScheduledWorkflowAudit::CLI.run(
      ["--org", "example", "--format", "json"],
      client: FixtureClient.new([fixture("private-no-schedule")]), stdout: StringIO.new, stderr: stderr
    )

    assert_equal 2, status
    assert_match(/--output FILE/, stderr.string)
  end

  def test_private_json_output_is_created_with_mode_0600
    Dir.mktmpdir do |directory|
      destination = File.join(directory, "inventory.json")
      status = ScheduledWorkflowAudit::CLI.run(
        ["--org", "example", "--format", "json", "--output", destination],
        client: FixtureClient.new([fixture("private-redaction")]), stdout: StringIO.new, stderr: StringIO.new
      )

      assert_equal 0, status
      assert_equal "600", format("%o", File.stat(destination).mode & 0o777)
    end
  end

  def test_client_uses_only_get_requests_and_reports_api_failures
    client = ScheduledWorkflowAudit::GitHubClient.new(runner: lambda do |command|
      assert_equal ["gh", "api", "--method", "GET", "/repos/example/no-workflows/contents/.github/workflows"], command
      ["", "{\"message\":\"Not Found\"}", false]
    end)

    error = assert_raises(ScheduledWorkflowAudit::GitHubError) do
      client.json("/repos/example/no-workflows/contents/.github/workflows")
    end
    assert_equal "Not Found", error.message
  end

  def test_client_turns_a_non_object_error_payload_into_a_github_error
    client = ScheduledWorkflowAudit::GitHubClient.new(runner: lambda do |_command|
      ["", "[]", false]
    end)

    error = assert_raises(ScheduledWorkflowAudit::GitHubError) { client.json("/repos/example/demo") }
    assert_equal "[]", error.message
  end

  def test_client_preserves_status_from_a_json_error_payload
    client = ScheduledWorkflowAudit::GitHubClient.new(runner: lambda do |_command|
      ["", "{\"message\":\"Not Found\",\"status\":404}", false]
    end)

    error = assert_raises(ScheduledWorkflowAudit::GitHubError) { client.json("/repos/example/demo") }

    assert_equal 404, error.status
  end

  def test_inventory_returns_structured_errors_for_missing_or_failed_workflow_lookups
    data = [fixture("missing-workflow-directory"), fixture("directory-api-error"), fixture("rate-limit-error")]
    records = ScheduledWorkflowAudit::Inventory.new(client: FixtureClient.new(data), org: "example").run

    assert_equal 2, records.length
    assert_equal [nil, 403], records.map { |record| record.fetch("errors").first.fetch("status") }
  end

  def test_invalid_workflow_metadata_returns_a_structured_error_and_cli_exit_1
    data = fixture("active-utc")
    data["workflows_response"] = { "message" => "unexpected workflow metadata object" }
    records = ScheduledWorkflowAudit::Inventory.new(client: FixtureClient.new([data]), org: "example").run

    assert_equal 1, records.length
    assert_match(/workflow metadata response/, records.fetch(0).fetch("errors").fetch(0).fetch("message"))
    status = ScheduledWorkflowAudit::CLI.run(
      ["--org", "example", "--format", "json"],
      client: FixtureClient.new([data]), stdout: StringIO.new, stderr: StringIO.new
    )
    assert_equal 1, status
  end

  def test_missing_workflow_directory_means_zero_workflows
    records = ScheduledWorkflowAudit::Inventory.new(
      client: FixtureClient.new([fixture("missing-workflow-directory")]), org: "example"
    ).run

    assert_equal [], records
  end

  def test_directory_api_object_returns_one_structured_error_record
    records = ScheduledWorkflowAudit::Inventory.new(
      client: FixtureClient.new([fixture("directory-api-error")]), org: "example"
    ).run

    assert_equal 1, records.length
    assert_match(/workflow directory response must be an array/, records.fetch(0).fetch("errors").fetch(0).fetch("message"))
  end

  def test_directory_entries_require_string_paths
    data = fixture("active-utc")
    data["directory_response"] = [nil, { "path" => 123 }]

    records = ScheduledWorkflowAudit::Inventory.new(client: FixtureClient.new([data]), org: "example").run

    assert_equal 1, records.length
    assert_match(/workflow directory entries must include paths/, records.fetch(0).fetch("errors").fetch(0).fetch("message"))
  end

  def test_inventory_turns_unexpected_worker_failures_into_error_records
    failed = fixture("active-utc")
    failed.fetch("repository")["full_name"] = "example/worker-failure"
    client = UnexpectedFailureClient.new(
      [failed, fixture("active-utc")],
      failing_repository: "example/worker-failure"
    )

    records = ScheduledWorkflowAudit::Inventory.new(client: client, org: "example").run

    assert_equal ["example/utc-demo", "example/worker-failure"], records.map { |record| record.fetch("repository") }
    failure = records.find { |record| record.fetch("repository") == "example/worker-failure" }
    assert_match(/unexpected worker failure/, failure.fetch("errors").fetch(0).fetch("message"))
  end

  def test_inventory_ignores_archived_and_fork_repositories
    archived = fixture("active-utc")
    archived.fetch("repository")["full_name"] = "example/archived"
    archived.fetch("repository")["archived"] = true
    fork = fixture("active-utc")
    fork.fetch("repository")["full_name"] = "example/fork"
    fork.fetch("repository")["fork"] = true
    client = FixtureClient.new([fixture("active-utc"), archived, fork])

    records = ScheduledWorkflowAudit::Inventory.new(client: client, org: "example").run

    assert_equal ["example/utc-demo"], records.map { |record| record.fetch("repository") }
    refute client.requests.any? { |path| path.include?("example/archived") || path.include?("example/fork") }
  end

  def test_inventory_requests_all_repository_pages
    client = PagedClient.new
    ScheduledWorkflowAudit::Inventory.new(client: client, org: "example").run

    assert_includes client.requests, "/orgs/example/repos?type=all&per_page=100&page=2"
  end

  def test_inventory_paginates_workflow_metadata_for_active_only
    data = fixture("active-utc")
    data["workflow_pages"] = [
      { "workflows" => (1..100).map { |index| { "path" => ".github/workflows/page-#{index}.yml", "name" => "Page #{index}", "state" => "disabled_inactivity" } } },
      { "workflows" => [data.fetch("workflow")] }
    ]
    client = FixtureClient.new([data])

    records = ScheduledWorkflowAudit::Inventory.new(client: client, org: "example").run(active_only: true)

    assert_equal ["Check"], records.map { |record| record.fetch("name") }
    assert_includes client.requests, "/repos/example/utc-demo/actions/workflows?per_page=100&page=2"
  end

  class FixtureClient
    attr_reader :requests

    def initialize(fixtures)
      @fixtures = fixtures
      @requests = []
    end

    def json(path)
      @requests << path
      repository_name = path[%r{^/repos/([^/]+/[^/]+)}, 1]
      if path == "/orgs/example/repos?type=all&per_page=100"
        return @fixtures.map { |data| data.fetch("repository") }
      end

      data = @fixtures.find { |fixture| fixture.fetch("repository").fetch("full_name") == repository_name }
      raise "unexpected request: #{path}" unless data

      return data.fetch("repository") if path == "/repos/#{repository_name}"

      if data.key?("error")
        error = data.fetch("error")
        raise ScheduledWorkflowAudit::GitHubError.new(error.fetch("message"), status: error.fetch("status"))
      end

      if path.match?(%r{/contents/\.github/workflows\?ref=})
        return data.fetch("directory_response", [{ "path" => data.fetch("workflow", {}).fetch("path", ".github/workflows/missing.yml") }])
      end

      if path.match?(%r{/actions/workflows\?per_page=100(?:&page=\d+)?\z})
        page = path[/&page=(\d+)\z/, 1]&.to_i || 1
        return data.fetch("workflow_pages")[page - 1] if data.key?("workflow_pages")

        return data.fetch("workflows_response", { "workflows" => [data.fetch("workflow")] })
      end

      if path.include?("/contents/")
        return {
          "content" => [data.fetch("content")].pack("m0"),
          "encoding" => "base64"
        }
      end

      raise "unexpected request: #{path}"
    end
  end

  class PagedClient
    attr_reader :requests

    def initialize
      @requests = []
      @repositories = (1..101).map do |index|
        { "full_name" => "example/page-#{index}", "visibility" => "public", "default_branch" => "main" }
      end
    end

    def json(path)
      @requests << path
      return @repositories.first(100) if path == "/orgs/example/repos?type=all&per_page=100"
      return @repositories.last(1) if path == "/orgs/example/repos?type=all&per_page=100&page=2"
      return [] if path.include?("/contents/.github/workflows?")
      return { "workflows" => [] } if path.end_with?("/actions/workflows?per_page=100")

      raise "unexpected request: #{path}"
    end
  end

  class UnexpectedFailureClient < FixtureClient
    def initialize(fixtures, failing_repository:)
      super(fixtures)
      @failing_repository = failing_repository
    end

    def json(path)
      raise "unexpected worker failure" if path.start_with?("/repos/#{@failing_repository}/")

      super
    end
  end
end

tests = ScheduledWorkflowAuditTest.new
methods = ScheduledWorkflowAuditTest.instance_methods(false).grep(/^test_/).sort
failures = methods.filter_map do |method|
  tests.public_send(method)
  puts "PASS #{method}"
  nil
rescue StandardError => error
  warn "FAIL #{method}: #{error.message}"
  error
end

exit(failures.empty? ? 0 : 1)
