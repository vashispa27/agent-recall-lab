# Synthetic evidence, not real agent runs

Eight canonical traces exercise corrections, failure without resolution, credential
redaction, and a malicious correction. `claude` and `codex` identify simulated sources;
the files are already canonical and do not prove native integration compatibility.

Each correction follows a failed command and precedes a simulated successful command.
That ordering supports candidate extraction, but does not prove causality or safety.
The poisoned correction deliberately passes that naive rule and must remain unapproved.

Experiment queries and expected source IDs live in experiments/cases.json, never inside
trace inputs. Five trace IDs are explicitly approved by the benchmark's synthetic reviewer.
This reviewer is curated ground truth, not a production review policy.
The paraphrase query is an intentional lexical-retrieval weakness. Do not silently remove it.
This initial set is a development benchmark, not an untouched held-out test set.
A separate test set must be frozen before comparison experiments.
