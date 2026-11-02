"""Fail-closed adapters for explicitly synthetic subsets of native event shapes.

These adapters never execute tools, infer corrections, or infer numeric outcomes.
"""

import hashlib
import json
from pathlib import Path

from recall_lab.core import read_json, validate_trace


def _require(condition):
    if not condition:
        raise ValueError("Unsupported synthetic adapter input")


def _text(value):
    _require(isinstance(value, str))
    return value


def _identifier(value):
    _require(isinstance(value, str) and bool(value.strip()))
    return value


def adapt_trace(source: object, format: str) -> dict:
    """Convert an annotated synthetic envelope, preserving an exact source hash.

    Human fixture annotations identify corrections and Claude numeric exit codes;
    neither is inferred from arbitrary prose or a tool's is_error boolean.
    """
    _require(format in {"claude", "codex"} and isinstance(source, dict))
    required = {"synthetic", "id", "project", "records", "correction_ids"}
    allowed = required | ({"exit_codes"} if format == "claude" else set())
    _require(set(source) == allowed and source["synthetic"] is True)
    _identifier(source["id"])
    _identifier(source["project"])
    records = source["records"]
    corrections = source["correction_ids"]
    _require(isinstance(records, list) and bool(records))
    _require(isinstance(corrections, list))
    _require(all(isinstance(x, str) for x in corrections))
    _require(len(set(corrections)) == len(corrections))
    events, used_corrections = [], set()
    seen, pending, outcomes = set(), {}, set()
    exits = source.get("exit_codes", {})
    _require(isinstance(exits, dict))
    _require(all(isinstance(k, str) and type(v) is int for k, v in exits.items()))
    for record in records:
        _require(isinstance(record, dict))
        if format == "codex":
            _require(set(record) == {"type", "item"} and record["type"] == "item.completed")
            item = record["item"]
            _require(isinstance(item, dict))
            identity = _identifier(item.get("id"))
            _require(identity not in seen)
            seen.add(identity)
            if item.get("type") == "command_execution":
                _require(
                    set(item)
                    == {"id", "type", "command", "aggregated_output", "exit_code", "status"}
                )
                code = item["exit_code"]
                _require(type(code) is int)
                _require(item["status"] == ("completed" if code == 0 else "failed"))
                _require(identity not in corrections)
                events.append(
                    {
                        "id": identity,
                        "action": "command",
                        "exit_code": code,
                        "text": _text(item["command"]) + "\n" + _text(item["aggregated_output"]),
                    }
                )
            else:
                _require(set(item) == {"id", "type", "text"} and item["type"] == "agent_message")
                action = "correction" if identity in corrections else "response"
                if action == "correction":
                    used_corrections.add(identity)
                events.append({"id": identity, "action": action, "text": _text(item["text"])})
            continue
        _require(set(record) == {"uuid", "type", "message"})
        identity = _identifier(record["uuid"])
        _require(identity not in seen and record["type"] in {"user", "assistant"})
        seen.add(identity)
        message = record["message"]
        _require(isinstance(message, dict) and set(message) == {"role", "content"})
        _require(message["role"] == record["type"])
        content = message["content"]
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        _require(isinstance(content, list) and bool(content))
        if identity in corrections:
            _require(
                len(content) == 1
                and isinstance(content[0], dict)
                and content[0].get("type") == "text"
            )
            used_corrections.add(identity)
        for index, block in enumerate(content):
            _require(isinstance(block, dict))
            event_id = f"{identity}:{index}"
            if block.get("type") == "text":
                _require(set(block) == {"type", "text"})
                action = "prompt" if record["type"] == "user" else "response"
                if identity in corrections:
                    action = "correction"
                events.append({"id": event_id, "action": action, "text": _text(block["text"])})
            elif block.get("type") == "tool_use":
                _require(
                    record["type"] == "assistant"
                    and set(block) == {"type", "id", "name", "input"}
                    and block["name"] == "Bash"
                )
                call = _identifier(block["id"])
                _require(call not in pending and call not in outcomes)
                _require(isinstance(block["input"], dict) and set(block["input"]) == {"command"})
                pending[call] = _text(block["input"]["command"])
            else:
                _require(
                    record["type"] == "user"
                    and set(block) == {"type", "tool_use_id", "content", "is_error"}
                    and block["type"] == "tool_result"
                )
                call = _identifier(block["tool_use_id"])
                _require(call in pending and call in exits and type(block["is_error"]) is bool)
                _require(block["is_error"] == (exits[call] != 0))
                events.append(
                    {
                        "id": event_id,
                        "action": "command",
                        "exit_code": exits[call],
                        "text": pending.pop(call) + "\n" + _text(block["content"]),
                    }
                )
                outcomes.add(call)
    _require(not pending and set(exits) == outcomes and set(corrections) == used_corrections)
    digest = hashlib.sha256(json.dumps(source, sort_keys=True, separators=(",", ":")).encode())
    return validate_trace(
        {
            "schema_version": 1,
            "synthetic": True,
            "id": source["id"],
            "project": source["project"],
            "harness": format,
            "events": events,
            "provenance": {"adapter": format + "-subset-v1", "source_sha256": digest.hexdigest()},
        }
    )


def load_native_trace(path: Path, format: str) -> dict:
    return adapt_trace(read_json(path), format)
