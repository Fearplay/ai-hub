# AI Hub

> Czech version: [README.cs.md](README.cs.md).

> **Built with [Cursor](https://cursor.com)** - the AI editor that
> wrote the bulk of this codebase (architecture, sections, AI pipelines,
> build script). The agent rules under
> [.cursor/rules/](.cursor/rules/) define how new sections, AI calls,
> and the `.exe` build are added so contributions stay consistent.

A desktop AI Hub built in Python with [Flet](https://flet.dev). Three-column
layout: navigation in the left sidebar, the main workspace in the middle,
and a context panel on the right. The **AI CV / Career** section is fully
wired to OpenAI / Anthropic; other sections share the same architecture
and are being filled in as we go.

## Requirements

- Python 3.10+
- Flet >= 0.25.0 (tested on 0.84.0)
- API keys (optional - without them the app runs in Demo mode):
  - **OpenAI** (`sk-...`) or **Anthropic** (`sk-ant-...`) under **Settings**
  - **GitHub** personal access token (optional, lifts the rate limit for AI Career)

> No Flutter SDK or Visual Studio C++ workload is required. Builds run
> through `flet pack` (PyInstaller), which only needs a plain Python on
> `PATH`.

## Install (development)

```bash
python -m venv .venv
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Run in dev mode

```bash
py main.py            # Windows
python main.py        # macOS / Linux
```

The upload zones in **AI Legal assistant** and **AI CV / Career** are
*click-to-browse* (they open the native file picker). Real OS-level
drag-and-drop would require `flet-dropzone` + `flet build`, which adds a
Flutter SDK + Visual Studio C++ dependency - we deliberately avoid that
because it would break the one-click build flow for collaborators (see
`build_exe.bat`).

## Build the .exe (Windows)

For Windows distribution, the repo root contains [`build_exe.bat`](build_exe.bat).
Double-clicking it produces a single `dist\AIHub.exe` that runs on a
clean PC without Python, virtualenv, or any SDK.

What the script does:

1. If Python isn't on `PATH`, it installs it via
   `winget install -e --id Python.Python.3.13`. If `winget` isn't
   available either, it prints a python.org link and exits.
2. If `.venv\` doesn't exist, it creates one.
3. Activates the venv and installs `requirements.txt` + `pyinstaller`.
4. Runs `flet pack main.py --name AIHub` and produces `dist\AIHub.exe`.

Usage:

```bat
build_exe.bat            REM standard build (skipped when the exe is newer than the sources)
build_exe.bat --force    REM always rebuild, even when nothing changed
```

Trade-off: `flet pack` (unlike `flet build windows`) **does not need the
Flutter SDK or Visual Studio C++**, so the build works on a clean
Windows machine. The price is that real OS file drag-and-drop is not
available - upload zones react to click and open the native file picker
instead.

The Cursor rule [`.cursor/rules/build-exe.mdc`](.cursor/rules/build-exe.mdc)
makes the agent run `build_exe.bat` at the end of every task, so
`dist\AIHub.exe` stays in sync with the sources.

### For collaborators (identical environment, no copy/paste)

Build artefacts (`AIHub.spec`, `.venv\`, `dist\`, `build\`) are all in
[.gitignore](.gitignore), so nothing is shared by hand. A second
contributor gets the exact same environment with:

1. `git clone <repo-url>`
2. `cd ai-hub`
3. `build_exe.bat` (one click)

The script:

- Installs Python via `winget` if missing.
- Creates a local `.venv\` and installs `requirements.txt` exactly as you
  see it (commit-pinned).
- `flet pack` generates **its own** `AIHub.spec` (the one you might see
  locally is just an artefact of the last build, it doesn't belong in
  git).
- Produces `dist\AIHub.exe`.

If you only want dev mode (no exe), steps 1-2 plus
`pip install -r requirements.txt` and `py main.py` are enough - see
*[Install (development)](#install-development)*.

## API keys and where they live

The **Settings** section (in the sidebar, under the divider) lets you:

- pick the AI provider (**OpenAI** / **Anthropic**) and model
  (defaults: `gpt-5.4-mini` / `claude-haiku-4-5`),
- save and delete API keys (OpenAI / Anthropic / GitHub),
- toggle global flags (Demo mode, follow-up questions),
- open the **Debug logs** viewer (view / copy / clear / open folder).

Keys are not written to disk in plain text. The app pushes them to the
OS-native secret store via [`keyring`](https://pypi.org/project/keyring/):

| OS | Backend |
| --- | --- |
| Windows | Credential Manager |
| macOS | Keychain |
| Linux | Secret Service / KWallet (when installed) |

When `keyring` has no available backend (typically headless Linux without
`gnome-keyring`), the Settings UI flips to read-only and explains what to
install.

### Demo mode (offline, no tokens)

Every AI section has a **Try demo data** button in Setup which walks the
whole workflow without calling any provider. Useful for screenshots,
demos, and the first walk-through of the app.

### Debug logs

When a click looks like it "did nothing" (theme/lang toggle, mode tab,
save), the app keeps a small log file:

- Path: `~/AI Hub/logs/app.log` (rotated at 1 MB, max 4 files).
- Open **Settings -> Debug logs -> View logs** in the app. You can
  refresh the view, copy the file to the clipboard, open the folder in
  the OS file browser, or clear it.
- No personal data is logged - only what was clicked, what succeeded,
  and the stack trace of any caught exception.

## Project structure

```
ai-hub/
├── main.py                       # entry point
├── requirements.txt
├── README.md                     # English (this file)
├── README.cs.md                  # Czech translation
├── CONTRIBUTING.md
├── LICENSE
├── .gitignore
└── src/
    ├── theme.py                  # design tokens (dark + light)
    ├── app.py                    # AIHubApp - state, layout, routing (no per-section knowledge)
    ├── i18n.py                   # global EN/CS strings + t(key, lang)
    ├── components/               # shared UI primitives
    │   ├── sidebar.py            # iterates the section registry, header / scroll / footer
    │   ├── nav_item.py
    │   ├── user_card.py
    │   ├── section_card.py
    │   ├── document_chip.py
    │   ├── header.py             # generic (icon, title, subtitle, ? button)
    │   ├── how_to_dialog.py      # generic "How to use" modal
    │   ├── tab_bar.py            # generic tab strip
    │   ├── chat_message.py
    │   ├── chat_input.py
    │   ├── context_panel.py      # shell + helpers for the right panel
    │   ├── language_toggle.py    # EN / CS toggle
    │   ├── theme_toggle.py       # dark / light toggle
    │   └── placeholder.py        # default "coming soon" view
    ├── services/                 # SHARED INFRASTRUCTURE - the only entry point for AI
    │   ├── secrets.py             # keyring wrapper (OS-native API key storage)
    │   ├── settings_store.py      # JSON preferences (provider, model, flags)
    │   ├── ai_provider.py         # run(system, user, schema, ...) -> OpenAI / Anthropic
    │   ├── cost_tracker.py        # session counter (calls / tokens / $)
    │   ├── job_scraper.py         # URL -> job posting text
    │   ├── file_parser.py         # PDF / DOCX / TXT / HTML -> plain text
    │   ├── github_client.py       # public profile + repo summary
    │   ├── exporter.py            # Markdown -> MD / HTML / DOCX / PDF
    │   ├── store.py               # JSON-backed history & run output paths
    │   └── logger.py              # rotating debug log under ~/AI Hub/logs/app.log
    ├── sections/                 # FEATURE FOLDERS - 1 folder = 1 sidebar entry
    │   ├── __init__.py           # auto-discovery (PRIMARY + SECONDARY groups)
    │   ├── _base.py              # Section dataclass (with nav_group)
    │   ├── SECTION_TEMPLATE/     # template for a new section (READ ME)
    │   ├── dashboard/
    │   ├── ai_career/            # fully wired to AI (HR expert, CV / cover letter)
    │   ├── ai_legal/              # fully built (4 working tabs + drag-drop)
    │   ├── ai_business/          # placeholder
    │   ├── ai_marketing/         # designed mock UI
    │   ├── ai_finance/           # placeholder
    │   ├── ai_study/             # placeholder
    │   ├── ai_documents/         # placeholder
    │   ├── ai_doc_assistant/     # PDF / DOCX assistant (summary / Q&A / rewrite / extract)
    │   ├── history/              # placeholder (secondary nav)
    │   ├── favorites/            # placeholder (secondary nav)
    │   └── settings/             # API keys, provider, general, debug logs (secondary nav)
    └── data/
        └── user.py               # global mock (the signed-in user only)
```

Every folder under `src/sections/` has:

- `section.py` - registration (`SECTION = Section(...)`)
- `view.py` - the main center column
- `strings.py` - EN + CS translations for that section
- `data.py` (optional) - mock data
- `context.py` (optional) - the right context panel

Adding a new section never opens `src/app.py` or `src/components/sidebar.py`.
Details in [CONTRIBUTING.md](CONTRIBUTING.md) and
[src/sections/SECTION_TEMPLATE/README.md](src/sections/SECTION_TEMPLATE/README.md).

## What it does

- Three-column layout, scrollable sidebar (header / scroll / footer).
- **Language toggle** EN <-> CS in the sidebar (default English, per the team).
- Section auto-discovery (primary + secondary; History / Favorites / Settings live in secondary).
- Light / dark mode toggle.
- **Settings** - API keys (OpenAI / Anthropic / GitHub) in the OS keystore, provider + model picker, demo flags, debug logs.
- **AI CV / Career** - two modes toggled in the section header:
  - **Chat** (Version B) - conversational HR assistant; you can attach documents (PDF / DOCX / TXT / MD / HTML) to a bubble and the context carries through follow-ups.
  - **Form mode** (Version A) - 4 stage tabs (Setup -> Match -> Documents -> History):
    - scrape the job posting from a URL or paste the text,
    - upload the resume (PDF / DOCX / TXT / HTML), optionally a LinkedIn export,
    - GitHub URL with automatic fetch of public repos,
    - 3 structured LLM steps (Candidate / JobSpec / MatchAnalysis) + per-document generators (Tailored CV, Modern CV, Cover Letter, Match Report, Interview Prep, Skill Gap, Evidence),
    - inline refine ("Problem 1, Problem 2..." -> AI revision),
    - export to MD / HTML / DOCX / PDF and save the full analysis to `outputs/<role>-<timestamp>/` (every "Save complete analysis" lands in a **fresh** timestamped folder).
  - Demo mode (offline showcase) in both modes.
  - HR-expert system prompt with no-hallucination clause, REORDER NEVER DELETE, CEFR-only, ATS rules, etc.
- **AI Marketing** - built from the supplied design (chat with an "Instagram post", phone mockup, brief panel).
- **AI Legal assistant** - 4 working tabs (Chat, Document analysis, Document drafts, Templates), OS drag-drop PDF, mock LLM.
- Right context panel showing **session cost** (calls / tokens / $) and the pipeline activity.

## Not yet (deliberately)

- Streaming responses in the UI (the first iteration blocks with a loader in the context panel).
- Multi-language `OUTPUT_LANGUAGE` per document (one run = one output language; driven by the global lang toggle).
- Real persistence for Favorites / History at the app level (currently per-section).
- AI in the remaining sections - the architecture is ready, sections are filled in following the AI Career template.

## Built with Cursor

This codebase was authored in [Cursor](https://cursor.com), the AI
editor. Cursor agents follow rules in [.cursor/rules/](.cursor/rules/)
that codify how to add a new section, where AI provider calls live, how
to log debug events, and how the `.exe` is rebuilt at the end of every
task. If you plan to extend the project, read those rules first - they
are the source of truth for how new code is added.

## Contributors

People working on this project:

<table>
  <tr>
    <td align="center" width="120">
      <a href="https://github.com/Fearplay">
        <img src="https://github.com/Fearplay.png" width="80" alt="Fearplay" />
        <br />
        <sub><b>Fearplay</b></sub>
      </a>
      <br />
      <sub>author &amp; maintainer</sub>
    </td>
    <td align="center" width="120">
      <a href="https://github.com/lukasekcerny">
        <img src="https://github.com/lukasekcerny.png" width="80" alt="lukasekcerny" />
        <br />
        <sub><b>lukasekcerny</b></sub>
      </a>
      <br />
      <sub>co-author</sub>
    </td>
  </tr>
</table>

Once the repo goes public this gallery can be replaced with the
auto-generated one:

```markdown
<a href="https://github.com/Fearplay/ai-hub/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Fearplay/ai-hub" alt="Contributors" />
</a>
```

Want to help? Branch / commit conventions are documented in
[CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

This project is licensed under the **MIT License** - see [LICENSE](LICENSE).

Libraries used:

| Library | License | Link |
| --- | --- | --- |
| [Flet](https://flet.dev) | Apache License 2.0 | https://github.com/flet-dev/flet/blob/main/LICENSE |

Apache 2.0 is fully compatible with MIT, so we can distribute this
project under MIT as long as we keep the upstream attribution (see
[LICENSE](LICENSE)).
