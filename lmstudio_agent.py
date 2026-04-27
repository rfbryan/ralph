#!/usr/bin/env python3
"""Run one Ralph iteration with LM Studio's Python SDK."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

try:
    import lmstudio as lms
except ImportError:
    print(
        "Error: lmstudio is not installed. Run `pip install -r requirements.txt`.",
        file=sys.stderr,
    )
    sys.exit(2)


MAX_TOOL_OUTPUT_CHARS = int(os.environ.get("LMSTUDIO_MAX_TOOL_OUTPUT_CHARS", "12000"))


def _trim_output(text: str) -> str:
    if len(text) <= MAX_TOOL_OUTPUT_CHARS:
        return text
    omitted = len(text) - MAX_TOOL_OUTPUT_CHARS
    return text[:MAX_TOOL_OUTPUT_CHARS] + f"\n\n[Output truncated: {omitted} characters omitted]"


def _resolve_workspace() -> Path:
    return Path(os.environ.get("RALPH_WORKSPACE", os.getcwd())).resolve()


WORKSPACE = _resolve_workspace()


def _resolve_path(path: str) -> Path:
    resolved = (WORKSPACE / path).resolve()
    try:
        resolved.relative_to(WORKSPACE)
    except ValueError as exc:
        raise ValueError(f"Path must stay within workspace: {WORKSPACE}") from exc
    return resolved


def list_directory(path: str = ".") -> str:
    """List files and directories at the given workspace-relative path."""
    target = _resolve_path(path)
    if not target.exists():
        return f"Error: path does not exist: {path}"
    if not target.is_dir():
        return f"Error: path is not a directory: {path}"

    entries = []
    for child in sorted(target.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
        suffix = "/" if child.is_dir() else ""
        entries.append(f"{child.name}{suffix}")
    return "\n".join(entries) if entries else "(empty directory)"


def read_file(path: str, start_line: int = 1, max_lines: int = 240) -> str:
    """Read a text file from the workspace with 1-based line numbers."""
    target = _resolve_path(path)
    if not target.exists():
        return f"Error: file does not exist: {path}"
    if not target.is_file():
        return f"Error: path is not a file: {path}"

    lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    start = max(start_line, 1) - 1
    end = min(start + max(max_lines, 1), len(lines))
    numbered = [f"{line_no}: {line}" for line_no, line in enumerate(lines[start:end], start + 1)]
    if end < len(lines):
        numbered.append(f"[Stopped at line {end}; {len(lines) - end} more lines available]")
    return "\n".join(numbered)


def write_file(path: str, content: str) -> str:
    """Create or overwrite a UTF-8 text file in the workspace."""
    target = _resolve_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} characters to {path}"


def append_file(path: str, content: str) -> str:
    """Append UTF-8 text to a file in the workspace, creating it if needed."""
    target = _resolve_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(content)
    return f"Appended {len(content)} characters to {path}"


def replace_in_file(path: str, old: str, new: str, expected_replacements: int = 1) -> str:
    """Replace exact text in a workspace file after verifying the expected match count."""
    target = _resolve_path(path)
    if not target.exists():
        return f"Error: file does not exist: {path}"
    if not target.is_file():
        return f"Error: path is not a file: {path}"

    content = target.read_text(encoding="utf-8", errors="replace")
    count = content.count(old)
    if count == 0:
        return "Error: old text was not found in the file."
    if expected_replacements >= 0 and count != expected_replacements:
        return f"Error: found {count} matches, expected {expected_replacements}."

    limit = count if expected_replacements < 0 else expected_replacements
    target.write_text(content.replace(old, new, limit), encoding="utf-8")
    return f"Replaced {limit} occurrence(s) in {path}"


def run_command(command: str, timeout_seconds: int = 120) -> str:
    """Run a shell command in the workspace using PowerShell on Windows and Bash elsewhere."""
    timeout = max(1, min(timeout_seconds, 1800))
    if os.name == "nt":
        args = ["powershell", "-NoProfile", "-Command", command]
    else:
        args = ["bash", "-lc", command]

    try:
        completed = subprocess.run(
            args,
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") + (exc.stderr or "")
        return _trim_output(f"Command timed out after {timeout} seconds.\n{output}")

    output = [
        f"Exit code: {completed.returncode}",
        "STDOUT:",
        completed.stdout or "",
        "STDERR:",
        completed.stderr or "",
    ]
    return _trim_output("\n".join(output))


def _print_fragment(fragment, round_index: int = 0) -> None:
    content = getattr(fragment, "content", "")
    print(content, end="", flush=True)


def _print_round_start(round_index: int) -> None:
    print(f"\n[LM Studio round {round_index + 1}]", file=sys.stderr, flush=True)


def _load_prompt(prompt_path: Path, script_dir: Path) -> str:
    prompt = prompt_path.read_text(encoding="utf-8")
    return f"""{prompt}

## Runtime Context

- Workspace root for tools: `{WORKSPACE}`
- Ralph directory: `{script_dir}`
- PRD path: `{script_dir / "prd.json"}`
- Progress path: `{script_dir / "progress.txt"}`
- Current process working directory: `{Path.cwd().resolve()}`
"""


def _configure_lmstudio() -> None:
    host = os.environ.get("LMSTUDIO_HOST", "").strip()
    if host:
        lms.configure_default_client(host)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one Ralph iteration via LM Studio.")
    parser.add_argument("--prompt", default="LMSTUDIO.md", help="Prompt file to send to the model.")
    parser.add_argument("--script-dir", default=None, help="Directory containing Ralph state files.")
    args = parser.parse_args()

    script_dir = Path(args.script_dir).resolve() if args.script_dir else Path(__file__).resolve().parent
    prompt_path = (script_dir / args.prompt).resolve()
    if not prompt_path.exists():
        print(f"Error: prompt file not found: {prompt_path}", file=sys.stderr)
        return 2

    _configure_lmstudio()
    model_key = os.environ.get("LMSTUDIO_MODEL", "").strip()
    model = lms.llm(model_key) if model_key else lms.llm()

    chat = lms.Chat("You are a task-focused autonomous coding agent.")
    chat.add_user_message(_load_prompt(prompt_path, script_dir))

    tools = [
        list_directory,
        read_file,
        write_file,
        append_file,
        replace_in_file,
        run_command,
    ]

    model.act(
        chat,
        tools,
        max_parallel_tool_calls=1,
        on_message=chat.append,
        on_prediction_fragment=_print_fragment,
        on_round_start=_print_round_start,
    )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
