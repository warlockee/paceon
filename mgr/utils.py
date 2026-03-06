"""
paceon mgr — Shared utilities and constants.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CTL_PATH: str = os.environ.get("PACEON_CTL", "./paceon-ctl")

# Provider detection: prefer Anthropic, fall back to Gemini
_anthropic_key: str = os.environ.get("ANTHROPIC_API_KEY", "")
_google_key: str = os.environ.get("GOOGLE_API_KEY", "")

if _anthropic_key:
    PROVIDER: str = "anthropic"
    API_KEY: str = _anthropic_key
    MODEL: str = os.environ.get("PACEON_MGR_MODEL", "claude-opus-4-6")
elif _google_key:
    PROVIDER = "gemini"
    API_KEY = _google_key
    MODEL = os.environ.get("PACEON_MGR_MODEL", "gemini-3-flash")
else:
    PROVIDER = ""
    API_KEY = ""
    MODEL = ""


def create_client() -> object:
    """Create and return the appropriate LLM client based on PROVIDER."""
    if PROVIDER == "anthropic":
        import anthropic
        return anthropic.Anthropic(api_key=API_KEY)
    elif PROVIDER == "gemini":
        from google import genai
        return genai.Client(api_key=API_KEY)
    else:
        raise RuntimeError(
            "No LLM API key found. Set ANTHROPIC_API_KEY or GOOGLE_API_KEY."
        )

MAX_CONVERSATION_TURNS: int = 30   # sliding window
MAX_TOOL_ROUNDS: int = 15          # max tool-use rounds per request
MAX_TASK_ITERATIONS: int = 100
MAX_TASK_TIMEOUT: int = 3600       # 1 hour
DEFAULT_POLL_INTERVAL: int = 10    # seconds

# Smart task (LLM-judged background tasks)
SMART_TASK_MODEL: str = os.environ.get("PACEON_SMART_TASK_MODEL", MODEL)
SMART_TASK_HISTORY_LIMIT: int = 10  # max conversation exchanges to keep

# Monitoring
MONITOR_INTERVAL: int = 3600       # health log every hour
MEMORY_LIMIT_MB: int = 500         # auto-restart if RSS exceeds this
TASK_PRUNE_AGE: int = 3600         # prune completed tasks older than 1 hour

# Output stability detection
DEFAULT_STABLE_SECONDS: int = 5    # output must be unchanged for this long
STABILITY_POLL: int = 2            # how often to re-capture while waiting
MAX_STABILITY_WAIT: int = 300      # max seconds to wait for stability (5 min)

# ---------------------------------------------------------------------------
# Output: send JSON lines to paceon (stdout)
# ---------------------------------------------------------------------------

_output_lock: threading.Lock = threading.Lock()

def send_response(chat_id: int, text: str) -> None:
    """Send a message back to paceon for delivery to Telegram."""
    if chat_id == 0:
        return  # Drop messages with no target
    msg = json.dumps({"chat_id": chat_id, "text": text}, ensure_ascii=False)
    with _output_lock:
        print(msg, flush=True)

# ---------------------------------------------------------------------------
# Shared ID counter for watchers and tasks
# ---------------------------------------------------------------------------

_task_id_counter: int = 0
_task_id_lock: threading.Lock = threading.Lock()

def _next_task_id() -> int:
    global _task_id_counter
    with _task_id_lock:
        _task_id_counter += 1
        return _task_id_counter

# ---------------------------------------------------------------------------
# Terminal operations via paceon-ctl
# ---------------------------------------------------------------------------

def ctl_run(args: list[str]) -> tuple[str, str, int]:
    """Run paceon-ctl with given args, return (stdout, stderr, returncode)."""
    try:
        result = subprocess.run(
            [CTL_PATH] + args,
            capture_output=True, text=True, timeout=15
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except FileNotFoundError:
        logger.error("paceon-ctl not found at %s", CTL_PATH)
        return "", f"paceon-ctl not found at {CTL_PATH}", 1
    except subprocess.TimeoutExpired:
        logger.warning("paceon-ctl timed out for args: %s", args)
        return "", "paceon-ctl timed out", 1
