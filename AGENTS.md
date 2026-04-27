# Ralph Agent Instructions

## Overview

Ralph is an autonomous AI agent loop that runs AI coding tools (Amp, Claude Code, Codex CLI, or LM Studio) repeatedly until all PRD items are complete. Each iteration is a fresh instance with clean context.

## Commands

```bash
# Run the flowchart dev server
cd flowchart && npm run dev

# Build the flowchart
cd flowchart && npm run build

# Run Ralph with Amp (default)
./ralph.sh [max_iterations]

# Run Ralph with Claude Code
./ralph.sh --tool claude [max_iterations]

# Run Ralph with Codex CLI
./ralph.sh --tool codex [max_iterations]

# Run Ralph with LM Studio
./ralph.sh --tool lmstudio [max_iterations]
```

## Key Files

- `ralph.sh` - The bash loop that spawns fresh AI instances (supports `--tool amp`, `--tool claude`, `--tool codex`, or `--tool lmstudio`)
- `prompt.md` - Instructions given to each AMP instance
- `CLAUDE.md` - Instructions given to each Claude Code instance
- `CODEX.md` - Instructions given to each Codex CLI instance
- `LMSTUDIO.md` - Instructions given to each LM Studio `.act()` instance
- `lmstudio_agent.py` - Python SDK runner for LM Studio with local file and shell tools
- `requirements.txt` - Python dependency list for LM Studio support
- `prd.json.example` - Example PRD format
- `flowchart/` - Interactive React Flow diagram explaining how Ralph works

## Flowchart

The `flowchart/` directory contains an interactive visualization built with React Flow. It's designed for presentations - click through to reveal each step with animations.

To run locally:
```bash
cd flowchart
npm install
npm run dev
```

## Patterns

- Each iteration spawns a fresh AI instance (Amp, Claude Code, Codex CLI, or LM Studio) with clean context
- Memory persists via git history, `progress.txt`, and `prd.json`
- Stories should be small enough to complete in one context window
- Always update AGENTS.md with discovered patterns for future iterations
- Codex runs through `codex exec` with `RALPH_DIR` pointing to the Ralph script directory; set `CODEX_MODEL` or `CODEX_PROFILE` to override Codex defaults.
- LM Studio runs through `lmstudio_agent.py`, which calls `model.act(...)`; set `LMSTUDIO_MODEL` to force a specific model key and `LMSTUDIO_HOST` for a non-default API host.
