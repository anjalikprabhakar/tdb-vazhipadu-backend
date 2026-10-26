"""PostToolUse hook: ruff-fix and ruff-format any Python file Claude just edited.

Reads the hook payload (JSON) from stdin. Never blocks the edit; lint problems that
ruff cannot fix are reported back to Claude via stderr with exit code 2.
"""

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    file_path = payload.get("tool_input", {}).get("file_path", "")
    if not file_path.endswith(".py") or not Path(file_path).exists():
        return 0

    subprocess.run(
        ["uv", "run", "ruff", "format", "--quiet", file_path], cwd=PROJECT_ROOT, check=False
    )
    lint = subprocess.run(
        ["uv", "run", "ruff", "check", "--fix", "--quiet", file_path],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if lint.returncode != 0:
        print(f"ruff found issues it could not auto-fix:\n{lint.stdout}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
