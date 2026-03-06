"""
paceon mgr — Tool definitions and terminal operation helpers.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from utils import ctl_run

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Terminal operations
# ---------------------------------------------------------------------------

def list_terminals() -> list[dict[str, Any]]:
    """List all available terminals. Returns list of dicts."""
    out, err, rc = ctl_run(["list"])
    if rc != 0:
        logger.error("list_terminals failed (rc=%d): %s", rc, err)
        return []
    try:
        return json.loads(out)
    except json.JSONDecodeError as e:
        logger.error("list_terminals JSON parse error: %s (output: %s)", e, out[:200])
        return []

_CAPTURE_LINES: int = 80  # Roughly one screen worth of output

def capture_terminal(terminal_id: str) -> str:
    """Capture full text from a terminal by ID (used for stability detection)."""
    out, err, rc = ctl_run(["capture", str(terminal_id)])
    if rc != 0:
        return f"[Error capturing terminal {terminal_id}: {err}]"
    return out

def capture_terminal_tail(terminal_id: str) -> str:
    """Capture last N lines from a terminal (used for LLM-facing reads)."""
    out = capture_terminal(terminal_id)
    if out.startswith("[Error"):
        return out
    lines = out.split('\n')
    if len(lines) > _CAPTURE_LINES:
        lines = lines[-_CAPTURE_LINES:]
    return '\n'.join(lines)

def send_keys(terminal_id: str, keys: str) -> str:
    """Send keystrokes to a terminal by ID."""
    # Translate literal control characters to the escape sequences
    # that the backend expects: \n → \\n (Enter), \t → \\t (Tab)
    keys = keys.replace('\n', '\\n')
    keys = keys.replace('\t', '\\t')
    out, err, rc = ctl_run(["send", str(terminal_id), keys])
    if rc != 0:
        return f"[Error sending keys to terminal {terminal_id}: {err}]"
    return "Keys sent successfully."

# ---------------------------------------------------------------------------
# Claude API tools
# ---------------------------------------------------------------------------

TOOLS: list[dict[str, Any]] = [
    {
        "name": "list_terminals",
        "description": "List all available terminal sessions with their IDs, names, and titles.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "read_terminal",
        "description": "Read/capture the current visible text from a terminal. Use the terminal's 'id' field (e.g., '12399' on macOS or '%%0' on tmux).",
        "input_schema": {
            "type": "object",
            "properties": {
                "terminal_id": {
                    "type": "string",
                    "description": "Terminal ID from list_terminals"
                }
            },
            "required": ["terminal_id"]
        }
    },
    {
        "name": "send_command",
        "description": (
            "Send keystrokes to a terminal and watch for the output to finish in the background. "
            "Returns immediately — the terminal is monitored asynchronously and the user is notified when "
            "the output stabilizes (stops changing). Use this for ALL commands. "
            "You do NOT need to guess if a command is fast or slow."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "terminal_id": {
                    "type": "string",
                    "description": "Terminal ID from list_terminals"
                },
                "keys": {
                    "type": "string",
                    "description": "Text/keystrokes to send. Use \\n for Enter, \\t for Tab."
                },
                "description": {
                    "type": "string",
                    "description": "Brief description of what this command does (shown in notification)"
                },
                "stable_seconds": {
                    "type": "number",
                    "description": "How many seconds the output must remain unchanged to be considered done. Default 5. Increase for slower programs."
                }
            },
            "required": ["terminal_id", "keys", "description"]
        }
    },
    {
        "name": "start_background_task",
        "description": (
            "Start a repeating background task that periodically sends input to a terminal "
            "and checks for a specific text condition. Useful for polling tasks like "
            "'keep asking until it says yes'. The task monitors output stability after each send."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "terminal_id": {
                    "type": "string",
                    "description": "Terminal ID to operate on"
                },
                "send_text": {
                    "type": "string",
                    "description": "Text to send to the terminal each iteration (empty string to just monitor)"
                },
                "check_contains": {
                    "type": "string",
                    "description": "Plain text substring to look for in terminal output. Task completes when found."
                },
                "description": {
                    "type": "string",
                    "description": "Human-readable description of what this task does"
                },
                "poll_interval": {
                    "type": "integer",
                    "description": "Seconds between sends/checks (default 10, minimum 5)"
                },
                "max_iterations": {
                    "type": "integer",
                    "description": "Maximum iterations before giving up (default 100)"
                }
            },
            "required": ["terminal_id", "check_contains", "description"]
        }
    },
    {
        "name": "list_tasks",
        "description": "List all background tasks and their status.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "cancel_task",
        "description": "Cancel a running background task by its ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "Task ID to cancel"
                }
            },
            "required": ["task_id"]
        }
    },
    {
        "name": "save_memory",
        "description": (
            "Save something to long-term memory. Persists across restarts. "
            "Use this when the user says 'remember', 'always', 'never', 'from now on', "
            "or when you learn important facts about their environment or preferences."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "What to remember (be specific and concise)"
                },
                "category": {
                    "type": "string",
                    "enum": ["rule", "knowledge", "preference"],
                    "description": "rule = user directives (always/never do X), knowledge = facts about environment, preference = style/behavior preferences"
                }
            },
            "required": ["content", "category"]
        }
    },
    {
        "name": "delete_memory",
        "description": "Delete a memory by its ID. Use when a memory is outdated or the user asks to forget something.",
        "input_schema": {
            "type": "object",
            "properties": {
                "memory_id": {
                    "type": "integer",
                    "description": "Memory ID to delete (from the memories list in context)"
                }
            },
            "required": ["memory_id"]
        }
    },
]
