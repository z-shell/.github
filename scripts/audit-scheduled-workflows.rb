#!/usr/bin/env ruby
# frozen_string_literal: true

require "json"
require "open3"
require "optparse"
require "time"
require "yaml"

module ScheduledWorkflowAudit
  SCHEMA = "z-shell/scheduled-workflow-audit/v1"

  class GitHubError < StandardError
    attr_reader :status

    def initialize(message, status: nil)
      super(message)
      @status = status
    end
  end

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

  class WorkflowParser
    def parse(repository:, metadata:, content:)
      workflow = YAML.safe_load(content, aliases: false)
      workflow = {} if workflow.nil?
      raise ArgumentError, "workflow must be a mapping" unless workflow.is_a?(Hash)

      triggers = workflow["on"] || workflow[true] || {}
      triggers = {} unless triggers.is_a?(Hash)
      schedules = Array(triggers["schedule"] || triggers[:schedule]).map do |entry|
        raise ArgumentError, "schedule entry must be a mapping" unless entry.is_a?(Hash)

        cron = entry["cron"] || entry[:cron]
        raise ArgumentError, "schedule entry must include cron" unless cron.is_a?(String) && !cron.empty?

        timezone = entry["timezone"] || entry[:timezone]
        timezone = "UTC" unless timezone.is_a?(String) && !timezone.empty?
        { "cron" => cron, "timezone" => timezone }
      end

      jobs = workflow["jobs"].is_a?(Hash) ? workflow.fetch("jobs") : {}
      {
        "schema" => SCHEMA,
        "repository" => repository.fetch("full_name"),
        "visibility" => repository.fetch("visibility", "public"),
        "default_branch" => repository.fetch("default_branch", "main"),
        "path" => metadata.fetch("path"),
        "name" => metadata.fetch("name"),
        "state" => metadata.fetch("state", "unknown"),
        "schedules" => schedules,
        "workflow_dispatch" => triggers.key?("workflow_dispatch") || triggers.key?(:workflow_dispatch),
        "permissions_locations" => locations(workflow, jobs, "permissions"),
        "concurrency_locations" => locations(workflow, jobs, "concurrency"),
        "reusable_calls" => reusable_calls(jobs),
        "errors" => []
      }
    rescue Psych::Exception => error
      raise ArgumentError, "invalid workflow YAML: #{error.message}"
    end

    private

    def locations(workflow, jobs, key)
      locations = []
      locations << "workflow" if workflow.key?(key) || workflow.key?(key.to_sym)
      locations << "job" if jobs.values.any? { |job| job.is_a?(Hash) && (job.key?(key) || job.key?(key.to_sym)) }
      locations
    end

    def reusable_calls(jobs)
      jobs.values.filter_map { |job| job["uses"] if job.is_a?(Hash) && job["uses"].is_a?(String) }
    end
  end

  class Inventory
    WORKER_COUNT = 12

    def initialize(client:, org:, repo: nil, public_only: false, parser: WorkflowParser.new)
      @client = client
      @org = org
      @repo = repo
      @public_only = public_only
      @parser = parser
    end

    def run(active_only: false)
      targets = target_repositories
      queue = Queue.new
      targets.each { |repository| queue << repository }
      records = []
      lock = Mutex.new
      workers = Array.new([targets.length, WORKER_COUNT].min) do
        Thread.new do
          loop do
            repository = queue.pop(true)
            result = begin
              records_for(repository, active_only: active_only)
            rescue StandardError => error
              [error_record(repository, {}, error)]
            end
            lock.synchronize { records.concat(result) }
          rescue ThreadError
            break
          end
        end
      end
      workers.each(&:join)
      records.sort_by { |record| [record.fetch("repository"), record["path"].to_s] }
    end

    def private_target_set?
      target_repositories.any? { |repository| repository.fetch("visibility", "public") != "public" }
    end

    private

    def repositories
      return [@client.json("/repos/#{@repo}")] if @repo

      page = 1
      repositories = []
      loop do
        suffix = page == 1 ? "" : "&page=#{page}"
        response = @client.json("/orgs/#{@org}/repos?type=all&per_page=100#{suffix}")
        raise ArgumentError, "repository response must be an array" unless response.is_a?(Array)

        repositories.concat(response)
        break if response.length < 100

        page += 1
      end
      repositories
    end

    def target_repositories
      @target_repositories ||= repositories.reject do |repository|
        repository["archived"] || repository["fork"] || (@public_only && repository.fetch("visibility", "public") != "public")
      end
    end

    def records_for(repository, active_only:)
      name = repository.fetch("full_name")
      directory = begin
        @client.json("/repos/#{name}/contents/.github/workflows?ref=#{repository.fetch("default_branch", "main")}")
      rescue GitHubError => error
        return [] if error.status == 404

        raise
      end
      raise GitHubError, "workflow directory response must be an array" unless directory.is_a?(Array)
      unless directory.all? { |entry| entry.is_a?(Hash) && entry["path"].is_a?(String) }
        raise ArgumentError, "workflow directory entries must include paths"
      end

      metadata_by_path = workflow_metadata(name).to_h { |workflow| [workflow.fetch("path"), workflow] }
      directory.filter_map do |entry|
        path = entry["path"]
        next unless path&.match?(/\.ya?ml\z/)

        metadata = metadata_by_path[path] || { "path" => path, "name" => File.basename(path), "state" => "unknown" }
        next if active_only && metadata.fetch("state", "unknown") != "active"

        content = @client.json("/repos/#{name}/contents/#{path}?ref=#{repository.fetch("default_branch", "main")}")
        record = @parser.parse(repository: repository, metadata: metadata, content: decode_content(content))
        record.fetch("schedules").empty? ? nil : record
      rescue GitHubError, ArgumentError => error
        error_record(repository, metadata || { "path" => path, "name" => File.basename(path), "state" => "unknown" }, error)
      end
    rescue GitHubError, ArgumentError => error
      [error_record(repository, {}, error)]
    end

    def decode_content(response)
      raise ArgumentError, "workflow content response must be an object" unless response.is_a?(Hash)
      raise ArgumentError, "workflow content must use base64 encoding" unless response["encoding"] == "base64"

      response.fetch("content").delete("\n").unpack1("m0")
    end

    def workflow_metadata(repository)
      page = 1
      workflows = []
      loop do
        suffix = page == 1 ? "" : "&page=#{page}"
        response = @client.json("/repos/#{repository}/actions/workflows?per_page=100#{suffix}")
        raise ArgumentError, "workflow metadata response must be an object" unless response.is_a?(Hash)

        current_page = response["workflows"]
        raise ArgumentError, "workflow metadata response must include a workflows array" unless current_page.is_a?(Array)
        unless current_page.all? { |workflow| workflow.is_a?(Hash) && workflow["path"].is_a?(String) }
          raise ArgumentError, "workflow metadata entries must include paths"
        end

        workflows.concat(current_page)
        break if current_page.length < 100

        page += 1
      end
      workflows
    end

    def error_record(repository, metadata, error)
      {
        "schema" => SCHEMA,
        "repository" => repository.fetch("full_name"),
        "visibility" => repository.fetch("visibility", "public"),
        "default_branch" => repository.fetch("default_branch", "main"),
        "path" => metadata["path"],
        "name" => metadata["name"],
        "state" => metadata["state"],
        "schedules" => [],
        "workflow_dispatch" => false,
        "permissions_locations" => [],
        "concurrency_locations" => [],
        "reusable_calls" => [],
        "errors" => [{ "status" => error.respond_to?(:status) ? error.status : nil, "message" => error.message }]
      }
    end
  end

  class Renderer
    def json(records)
      JSON.pretty_generate(records) + "\n"
    end

    def markdown(records, public_only:)
      # Markdown is always public-safe, even when the caller did not filter targets.
      visible = records.select { |record| record["visibility"] == "public" }
      lines = ["# Scheduled workflow inventory", "", "| Repository | Workflow | State | Schedules |", "| --- | --- | --- | --- |"]
      visible.each do |record|
        schedules = record.fetch("schedules").map { |schedule| "#{schedule.fetch("cron")} (#{schedule.fetch("timezone")})" }.join("<br>")
        lines << "| #{table_cell(record.fetch("repository"))} | #{table_cell(record["name"] || record["path"] || "Unavailable")} | #{table_cell(record["state"] || "unverified")} | #{table_cell(schedules)} |"
      end
      lines.join("\n") + "\n"
    end

    private

    def table_cell(value)
      value.to_s.gsub("|", "\\|").gsub(/\r?\n/, "<br>")
    end
  end

  class CLI
    def self.run(argv, client: GitHubClient.new, stdout: $stdout, stderr: $stderr)
      options = { org: nil, format: "json", public_only: false, active_only: false, output: nil, repo: nil }
      parser = OptionParser.new do |option|
        option.on("--org ORG") { |value| options[:org] = value }
        option.on("--format FORMAT", ["json", "markdown"]) { |value| options[:format] = value }
        option.on("--public-only") { options[:public_only] = true }
        option.on("--repo OWNER/REPO") { |value| options[:repo] = value }
        option.on("--active-only") { options[:active_only] = true }
        option.on("--output FILE") { |value| options[:output] = value }
      end
      forbidden = argv.find { |argument| argument.match?(/\A--(?:apply|update|delete|enable|disable|dispatch)(?:=|\z)/) }
      raise OptionParser::InvalidOption, forbidden if forbidden

      parser.parse!(argv)
      raise OptionParser::InvalidArgument, "--repo must be OWNER/REPO" if options[:repo] && !options[:repo].match?(%r{\A[^/]+/[^/]+\z})
      raise OptionParser::MissingArgument, "--org" if options[:repo].nil? && (options[:org].nil? || options[:org].empty?)

      inventory = Inventory.new(client: client, org: options[:org], repo: options[:repo], public_only: options[:public_only])
      if options[:format] == "json" && inventory.private_target_set? && options[:output].nil?
        stderr.puts "JSON for target sets that include private repositories requires --output FILE."
        return 2
      end
      records = inventory.run(active_only: options[:active_only])

      rendered = options[:format] == "json" ? Renderer.new.json(records) : Renderer.new.markdown(records, public_only: options[:public_only])
      if options[:output]
        write_output(options[:output], rendered)
      else
        stdout.write(rendered)
      end
      records.any? { |record| !record.fetch("errors").empty? } ? 1 : 0
    rescue OptionParser::ParseError, ArgumentError => error
      stderr.puts error.message
      2
    rescue GitHubError => error
      stderr.puts error.message
      1
    end

    def self.write_output(path, content)
      File.open(path, File::WRONLY | File::CREAT | File::TRUNC, 0o600) do |file|
        file.chmod(0o600)
        file.write(content)
      end
    end
  end
end

exit(ScheduledWorkflowAudit::CLI.run(ARGV)) if $PROGRAM_NAME == __FILE__
