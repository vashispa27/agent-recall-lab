# Enable project recall in Codex CLI

1. In the Agent Recall Lab checkout, run `uv sync --locked`. Keep that environment
   available to launch the local MCP server.
2. Use the [config template](../examples/integrations/codex/config.toml) to add the
   `mcp_servers.project_recall` table to `.codex/config.toml` at the root of the
   **target** project. Keep machine-specific paths local. Merge with any existing
   config. Set `command` to the lab checkout's absolute `.venv/bin/python` path
   on macOS or Linux. Set `--db` to the absolute path of your local SQLite database
   and `--project` to the exact key you use for capture and review.
3. Append the [recall instructions](../examples/integrations/codex/recall-instructions.md)
   to the target project's `AGENTS.md`. Preserve its existing instructions.
4. From the target project, run `codex mcp get project_recall` and check the launch
   arguments. Codex only loads project configuration for trusted projects. Review the
   project's config before trusting it. Start a fresh session and check that
   `project_recall` appears in `/mcp`.

The server keeps the same database and project binding for the session. Use a
different project-local configuration for each project. A project key is a retrieval
boundary for the tools. Protect the SQLite file with filesystem permissions.

[Capture and review](capture.md) are explicit operator actions. The server exposes
`recall` and `inspect_source` for approved memory in the configured project.
The project instructions cue Codex to use those tools at task start, before relevant
commands, and after a relevant failure. Codex still chooses whether to call a tool
and how to use its results. For a deterministic example of task-start and pre-command
callbacks, see the [controlled loop](../experiments/results/recall-loop.md).

Remove the table and instruction block to disable the integration in future sessions.
See [configuration and transport checks](../experiments/results/codex-recall.md)
for the verification scope.

[Official Codex project configuration](https://learn.chatgpt.com/docs/config-file/config-advanced#project-config-files-codexconfigtoml)
