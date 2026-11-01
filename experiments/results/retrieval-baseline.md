# Lexical retrieval baseline

Evidence type: synthetic retrieval evaluation. No LLM, agent harness, or fixture command
was executed by this benchmark. Reproduce with:

```bash
uv sync --locked --extra dev
uv run python experiments/retrieval_baseline.py --check
```

Eight synthetic traces produce six candidates. A curated benchmark reviewer approves five
ordinary lessons and leaves the poisoned correction unapproved. An unresolved failure and
the redaction fixture produce no candidates. The candidate rule does not detect poisoning;
review gating is the protection tested here.

| Measurement | Result |
| --- | --- |
| Relevant lesson ranked first | 5 / 6 positive queries (83.3%) |
| Correct abstention | 2 / 2 negative queries |
| Paraphrase query | Miss: no shared keywords |
| Live-model task success / token savings | Not measured |

The development set is tiny and curated. Expected answers identify trace IDs and are not
passed to extraction or retrieval. The lexical retriever scores overlap with lesson text;
its lack of semantic matching is visible in the paraphrase failure. These results do not
predict production performance and do not demonstrate improved agent behavior.

The fixture wording was clarified during initial testing so the generated-client lesson
explicitly names the client; this is a development benchmark and was not held out. Freeze
an independent test set before future comparative tuning. Exact per-case outputs and the
dataset hash are in [retrieval-baseline.json](retrieval-baseline.json).
