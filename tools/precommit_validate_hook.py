#!/usr/bin/env python3
"""PreToolUse hook (Claude Code): run validate_quiz_data.py before any `git
commit` and block the commit if it fails.

Mirrors LFCxBVB's claude-portable/scripts/block_commit_on_main.py — same
mechanism (PreToolUse on Bash, JSON permissionDecision:"deny" to block),
different purpose. Fails open: if the hook itself errors, the commit proceeds
rather than silently wedging.

CLAUDE.md already documents "每次更新...後，必須跑
python3 tools/validate_quiz_data.py" as a manual step; this makes it
mechanical instead of relying on Claude remembering.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Same segment-anchored pattern as block_commit_on_main.py: `git` must start a
# command segment, optional global flags, then `commit` — avoids matching
# "git commit" sitting inside a quoted argument to another command.
_COMMIT = re.compile(
    r"(?:^|[;&|(]|&&|\|\|)\s*git\b(?:\s+-\S+(?:\s+\S+)?)*\s+commit\b")


def _deny(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}))


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return  # malformed → don't interfere
    cmd = data.get("tool_input", {}).get("command", "")
    unquoted = re.sub(r"\"[^\"]*\"|'[^']*'", "", cmd)
    if not _COMMIT.search(unquoted):
        return  # not a git commit

    try:
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "validate_quiz_data.py")],
            cwd=str(ROOT), capture_output=True, text=True, timeout=30,
        )
    except Exception:
        return  # can't run the validator → fail open

    if result.returncode != 0:
        output = (result.stdout + result.stderr).strip()
        _deny(
            "validate_quiz_data.py 沒過，commit 已擋下——先修好 round／重複／"
            "alreadyKnown 不一致再 commit。輸出：\n" + output
        )


if __name__ == "__main__":
    main()
