# Codex project recall configuration checks

The [setup guide](../../docs/codex-recall.md) uses a project-local MCP table and an
optional project instruction block. Configuration and transport were checked separately.

| Check | Result | Evidence |
| --- | --- | --- |
| Trusted project loads the local server table | Pass | Codex CLI 0.155.1 returned the configured stdio command, database and project key. Paths contained spaces and remained single arguments. |
| Untrusted project ignores the local server table | Pass | The same CLI reported that the server name was absent. |
| Launch from outside the lab checkout | Pass | The Python MCP client launched the server in a temporary directory using the config template's module and arguments with disposable values. |
| Review, project and provenance boundaries | Pass | The same subprocess passed all 11 [protocol cases](mcp-smoke.json), including hidden candidates, project binding and source inspection. |

For the configuration checks, create a temporary Git project with the template
in `.codex/config.toml` and substitute absolute paths as in the setup guide. Use a
temporary Codex home with a `[projects."/absolute/path/to/temporary/project"]`
table in its `config.toml`. From the temporary project, run
`codex mcp get project_recall --json` with `CODEX_HOME` pointed at that home.
Repeat with `trust_level = "trusted"` and `trust_level = "untrusted"`.
This command reads configuration without starting a model session.

Run `uv run python experiments/mcp_smoke.py --check` from the lab checkout to
reproduce the stdio calls. The experiment uses the existing synthetic dataset and
records its hash in the per-case JSON. Run
`uv run python experiments/recall_loop.py --check` for the scripted callback
comparison. Task-start, pre-command and failure guidance in the Codex instruction
block depends on host tool use. The checks did not measure live tool selection,
lesson adoption or task improvement.
