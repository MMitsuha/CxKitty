# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CxKitty (超星学习通答题姬) is a Python automation tool for China's Chaoxing/ChaoxingStar learning platform. It automates course completion including video watching, chapter tests, document browsing, and exam handling. The project uses a Rich-based TUI for interactive operation.

## Development Commands

```bash
# Install dependencies
uv sync

# Run the application
uv run python3 main.py

# Format code (black, line-length 100)
uv run black .

# Sort imports
uv run isort .
```

There is no automated test suite. The Dockerfile still uses poetry (not yet migrated to uv).

## Architecture

### Layered Design

The codebase follows a three-layer architecture:

1. **TUI Layer** (`main.py`, `dialog.py`) — Rich-based terminal UI with split layouts, interactive prompts, and live-updating panels. `main.py` is the entry point that orchestrates the overall flow: login → class selection → task execution.

2. **Resolver Layer** (`resolver/`) — Task execution engines that bridge the UI and API layers:
   - `QuestionResolver` — Orchestrates answer searching across multiple searchers, ranks results by text similarity (difflib), and submits answers. Used for both chapter tests and exams.
   - `MediaPlayResolver` — Simulates video playback with configurable speed and report rate.
   - `DocumetResolver` — Handles document viewing completion.

3. **API Layer** (`cxapi/`) — Handles all HTTP communication with the Chaoxing platform:
   - `ChaoXingAPI` (`api.py`) — Root class for login (password with AES-CBC encryption, QR code), session lifecycle, face image fetching.
   - `SessionWraper` (`session.py`) — HTTP client with retry logic, captcha detection/OCR, and face recognition callback hooks.
   - `ExamDto` (`exam.py`) — Largest module (~860 lines). Manages exam sessions: metadata, question parsing, answer submission, and paper export.
   - `QAQDtoBase` (`base.py`) — Shared interface for question-answering operations (used by both `PointWorkDto` and `ExamDto`).
   - Task points in `task_point/` — Polymorphic handlers: `PointVideoDto`, `PointDocumentDto`, `PointWorkDto`.

### Searcher Plugin System

`resolver/searcher/` implements a plugin architecture for answer sources:
- `SearcherBase` — Interface with `invoke(question: QuestionModel) -> SearcherResp`.
- `MultiSearcherWraper` — Runs all configured searchers and aggregates results.
- Implementations: `JsonFileSearcher`, `SqliteSearcher`, `RestApiSearcher` (with JSONPath selectors), several third-party APIs (Enncy, CxSearcher, TiKuHai, LyCk6, Muke, Lemon), `OpenAISearcher`, `OllamaSearcherAPI`, `OaifreeSearcherAPI`.
- Searchers are configured in `config.yml` under the `searchers` list — each entry has a `type` field that maps to a searcher class.

### Configuration & Session Management

- `config.yml` — Central YAML config for all features, delays, searcher setup. Loaded by `config.py` into module-level constants.
- Sessions stored as JSON in `session/` directory. Multi-session support via `multi_session` toggle.
- Callback system for events: captcha recognition and face detection hooks are registered on `SessionWraper` and rendered in TUI panels.

### Data Flow

Login → Fetch classes → Select class → Fetch chapters → Iterate task points → Dispatch to resolver by type (`isinstance` checks) → Resolver uses searchers/API → Submit results → Wait between tasks.

## Key Conventions

- Python 3.10-3.11 required.
- Black formatter with `line-length = 100`.
- All user-facing strings and comments are in Chinese.
- Custom exceptions in `cxapi/exception.py`: `APIError`, `ChapterNotOpened`, `TaskPointError`, `HandleCaptchaError`.
- Data models use `dataclasses-json` for serialization (`cxapi/schema.py`).
- Logs written per-session to `logs/cxkitty_{phone}.log`.
- Question export as JSON to `export/` directory.
