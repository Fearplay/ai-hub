# AI Hub

> Czech version: [README.cs.md](README.cs.md).

> **Built with [Cursor](https://cursor.com)** - the AI editor that
> wrote the bulk of this codebase (architecture, sections, AI pipelines,
> build script). The agent rules under
> [.cursor/rules/](.cursor/rules/) define how new sections, AI calls,
> and the `.exe` build are added so contributions stay consistent.

A desktop AI Hub built in Python with
[PySide6](https://doc.qt.io/qtforpython-6/) (Qt 6 for Python).
Three-column layout: navigation in the left sidebar, the main workspace
in the middle, and a context panel on the right. **AI CV / Career** and
the new **AI LinkedIn Profile Builder** are fully wired to OpenAI /
Anthropic; other sections share the same architecture and are being
filled in as we go.

## Requirements

- Python 3.10+
- PySide6 >= 6.7.0 (Qt 6.x, ships its own Qt runtime - no extra SDK)
- API keys (optional - without them the app runs in Demo mode):
  - **OpenAI** (`sk-...`) or **Anthropic** (`sk-ant-...`) under **Settings**
  - **GitHub** personal access token (optional, lifts the rate limit for AI Career)

> No Flutter SDK, Qt SDK, or Visual Studio C++ workload is required.
> Builds run through `pyinstaller` (driven by `build_exe.bat`), which
> only needs a plain Python on `PATH`.

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

The upload zones in **AI Legal assistant**, **AI CV / Career**,
**AI LinkedIn Profile Builder**, and **AI Doc Assistant** all share one
component (`src/components/file_drop_zone.py`) that:

* Renders a dashed-border drop zone with a prominent "Click to browse"
  call-to-action - clicking opens the native file picker. There is no
  separate "Upload" button - the dashed zone *is* the button, which
  keeps the UI from having two redundant ways to do the same thing.
* Always shows a **Paste path** button beneath the zone. On Windows you
  can `Shift+Right-click` a file in Explorer -> *Copy as path*, then
  click the button - the file is loaded immediately.
* Accepts real **OS drag-and-drop** thanks to Qt's `dragEnterEvent` /
  `dropEvent` plumbing - drop a file from Explorer / Finder / Files
  directly onto the zone and it loads instantly.
* Accepts **PDF / DOCX / HTML / HTM / TXT / MD** files - the extracted
  text body is what feeds the AI prompts in **AI Legal**, **AI Career**
  and friends.

The clipboard handling itself is centralised in
`src/services/clipboard.py`. It is a thin synchronous wrapper around
[pyperclip](https://pypi.org/project/pyperclip/) (with `win32clipboard`
/ `pbcopy` / `xclip` / `tkinter` fallbacks) so Copy / Paste buttons stay
robust regardless of the Qt session state.

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
4. Runs `pyinstaller --onefile --windowed --name AIHub` (with the
   bundled Material Symbols Rounded icon font subset under
   `assets\fonts\` baked in) and produces `dist\AIHub.exe`.

Usage:

```bat
build_exe.bat            REM standard build (skipped when the exe is newer than the sources)
build_exe.bat --force    REM always rebuild, even when nothing changed
```

Trade-off: PyInstaller bundles PySide6's Qt 6 runtime into the .exe -
no Flutter SDK, no Qt SDK, no Visual Studio C++ workload required.
Real OS drag-and-drop **is** available because Qt handles the events
natively.

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
- `pyinstaller` generates **its own** `AIHub.spec` (the one you might
  see locally is just an artefact of the last build, it doesn't belong
  in git).
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

### HTTPS via the OS trust store

Every OpenAI / Anthropic / GitHub call ultimately flows through `httpx`,
which by default validates server certificates against the bundled
`certifi` CA list. On corporate / school networks (Zscaler, Netskope,
antivirus MITM, custom internal roots), the chain is only present in
the **OS** trust store, not in `certifi`, and the request fails with
`SSL: CERTIFICATE_VERIFY_FAILED`. To make HTTPS Just Work on those
machines, `main.py` calls
[`truststore.inject_into_ssl()`](https://truststore.readthedocs.io/) as
the very first runtime statement, which patches Python's `ssl.SSLContext`
to use:

| OS | Backend |
| --- | --- |
| Windows | CryptoAPI (Trusted Root Certification Authorities) |
| macOS | Security framework |
| Linux | OpenSSL system roots |

`truststore` is added to `requirements.txt` and bundled into the .exe via
`--collect-submodules truststore` in `build_exe.bat`. No section / library
code calls `inject_into_ssl()` - per the upstream warning, only the
application entry point is allowed to.

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
- The in-app viewer colours each row by level (red for `ERROR`, amber
  for `WARNING`, cyan for `DEBUG`, default for `INFO`, bold red for
  `CRITICAL`). The bytes on disk stay plain text - the colours live
  only in the viewer. The Settings page also uses the full window
  width so the column-aligned rows do not wrap.
- The viewer renders the tail in a `QPlainTextEdit` with a
  `QSyntaxHighlighter`, so you can drag-select across multiple rows
  with the mouse and press `Ctrl+C`, or use the **Copy** button at the
  top to grab the whole file. Copy goes through the OS clipboard
  (pyperclip) for cross-platform reliability.
- No personal data is logged - only what was clicked, what succeeded,
  and the stack trace of any caught exception.
- Format is column-aligned for fast skimming:

  ```
  2026-05-09 19:47:11.123 | INFO  | ai_career.pipeline     | activity_change            | prev=ready new=analyzing
  2026-05-09 19:47:14.886 | ERROR | ai_career.pipeline     | extract_candidate_failed   | error=ProviderError(...) elapsed_ms=3759
  2026-05-09 19:47:14.890 | ERROR | ai_career.pipeline     | extract_candidate_failed.traceback | Traceback (most recent call last): ...
  ```

  Long-running pipeline steps emit `*_start` / `*_done` / `*_failed`
  pairs with `elapsed_ms` so the log doubles as a coarse profiler
  (`@logger_service.timed_call` decorator in `src/services/logger.py`).

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
├── assets/
│   └── fonts/                     # bundled Material Symbols Rounded subset + codepoints
└── src/
    ├── theme.py                  # design tokens (dark + light)
    ├── app.py                    # AIHubApp - state, layout, routing (no per-section knowledge)
    ├── i18n.py                   # global EN/CS strings + t(key, lang)
    ├── qt/                        # PySide6 building blocks
    │   ├── theme.py              # QSS emitter + rgba helper
    │   ├── icons.py              # Material Symbols Rounded font loader + codepoint registry
    │   ├── widgets.py            # Card / IconLabel / ElidedLabel / typography / buttons / Pill
    │   ├── effects.py            # drop shadow + opacity helpers
    │   ├── markdown.py           # bold-spans helper for plain QLabel
    │   ├── dialog.py             # BaseDialog (themed modal scaffold)
    │   ├── runtime.py             # cross-thread UI dispatcher (worker -> GUI)
    │   └── window_chrome.py      # Win32 DWM helper - tints the OS title bar to match the theme
    ├── components/               # shared UI primitives (PySide6)
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
    │   ├── file_drop_zone.py     # shared upload zone (real OS drag-drop + click + paste-path)
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
    │   ├── exporter.py            # Markdown -> MD / HTML / DOCX / PDF (clickable PDF links)
    │   ├── html_pdf.py            # Playwright print-to-PDF (Modern CV + themed Cover Letter)
    │   ├── store.py               # JSON-backed history & run output paths
    │   └── logger.py              # rotating debug log + @timed_call + log_state helpers
    ├── sections/                 # FEATURE FOLDERS - 1 folder = 1 sidebar entry
    │   ├── __init__.py           # auto-discovery (PRIMARY + SECONDARY groups)
    │   ├── _base.py              # Section dataclass (with nav_group)
    │   ├── SECTION_TEMPLATE/     # template for a new section (READ ME)
    │   ├── dashboard/
    │   ├── ai_career/            # fully wired to AI (HR expert, CV / cover letter)
    │   ├── ai_linkedin/          # fully wired to AI (LinkedIn Profile Builder, 20+ sections)
    │   ├── ai_legal/              # AI-wired chat (multi-format upload + 4 quick actions)
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
- Light / dark mode toggle - the **Windows OS title bar** (caption strip with
  X / minimise / maximise + app name) is tinted to match the active theme via
  the DWM API, so dark mode no longer leaves a bright white strip on top of
  the dark sidebar (`src/qt/window_chrome.py`, no-op on macOS / Linux).
- **Snappy theme + language switch** - flipping the sidebar pill reapplies
  the global QSS, rebuilds the sidebar widget, and rebuilds **only** the
  active section's center + right column (other sections pick up the new
  language on their next click). The full window is no longer torn down on
  every toggle, so the previously-3-second freeze on the AI Career section
  is gone.
- **Settings** - API keys (OpenAI / Anthropic / GitHub) in the OS keystore, provider + model picker, demo flags, debug logs.
- **AI CV / Career** - two modes toggled in the section header:
  - **Chat** (Version B) - conversational HR assistant; you can attach documents (PDF / DOCX / TXT / MD / HTML) to a bubble and the context carries through follow-ups.
  - **Form mode** (Version A) - 4 stage tabs (Setup -> Match -> Documents -> History):
    - scrape the job posting from a URL or paste the text,
    - upload the resume (PDF / DOCX / TXT / HTML), optionally a LinkedIn export,
    - GitHub URL with automatic fetch of public repos,
    - 3 structured LLM steps (Candidate / JobSpec / MatchAnalysis) + per-document generators (Tailored CV, Modern CV, Cover Letter, Match Report, Interview Prep, Skill Gap, Evidence),
    - inline refine ("Problem 1, Problem 2..." -> AI revision),
    - export to MD / HTML / DOCX / PDF (with **clickable hyperlinks** in the PDF) and save the full analysis to `outputs/<role>-<timestamp>/` (every "Save complete analysis" lands in a **fresh** timestamped folder).
  - Demo mode (offline showcase) in both modes.
  - HR-expert system prompt with no-hallucination clause, REORDER NEVER DELETE, CEFR-only, ATS rules, etc.
- **AI LinkedIn Profile Builder** - same two-mode shell (Chat / Builder), aimed at a complete LinkedIn rewrite:
  - **Setup** - target roles, audience (recruiter / peer / customer), tone (professional / friendly / bold / academic), output language (EN / CS), CV + LinkedIn export uploads, GitHub URL, free-form notes.
  - **Sections** picker - presets (essentials / full polish / job hunt / thought leadership) + 12-section grid with checkboxes (Headline, About, Experience, Education, Certifications, Skills, Featured, Projects, Services, Courses, Recommendations, Posts).
  - One LLM **profile-extraction** call followed by per-section generators that all reuse the cached profile JSON (cost-aware - never re-sends the raw CV text).
  - **Anti-cringe + no-hallucination** prompts; an unsupported-claims report flags any AI bullet that wasn't backed by source evidence.
  - **Profile completeness checklist** with priority levels (critical / important / nice to have) and a 0-100 profile score.
  - **Output** tab renders every generated section as a card (with copy-to-clipboard) + the checklist + the score.
  - Save the complete profile to `outputs/<target-role>-<timestamp>/` as MD per section, the comprehensive `full_linkedin_profile.html` summary, and a JSON snapshot for future runs.
  - Demo mode (offline showcase) populates a curated end-to-end example in seconds.
- **AI Marketing** - built from the supplied design (chat with an "Instagram post", phone mockup, brief panel).
- **AI Legal assistant** - fully AI-wired chat with a legal document:
  - **Multi-format upload** - drag a `PDF`, `DOCX`, `HTML`, `TXT` (or `MD`) document onto the right-hand panel; the text body feeds the prompts, only the extracted plain text leaves your machine.
  - **Four quick-action chips** - Summarise / Find risks / Explain legal terms / Suggest changes - each opens a tailored prompt and streams the reply back into the chat. Plain typing in the input field also works.
  - **No-lawyer disclaimer** - inline banner under the header reminds the user the assistant does not replace legal advice; every long reply re-states it in plain language.
  - **Demo mode** - turn the global Demo flag on in **Settings** to walk the same UI without any provider call (returns a stubbed answer).
  - **Compact header** - the Legal section drops the trailing *How to use* / `…` buttons and uses a tighter top bar so the chat has more vertical space; other sections keep their full chrome via the new `show_help_button` / `show_menu_button` / `compact` flags on `src/components/header.py`.
- **Shared file-upload component** (`src/components/file_drop_zone.py`) - one place for click-to-browse, best-effort OS drag-and-drop, and clipboard-paste-path. AI Career, AI LinkedIn, and AI Legal all use it.
- Right context panel showing **session cost** (calls / tokens / $) and a real-time **Activity** badge that reflects the pipeline stage (`scraping`, `analyzing`, `generating`, `scoring`, `saving`, `error`, `ready`) - the badge updates from background worker threads via `REFS.request_context_refresh()` so the user never sees a stale "Ready" while the LLM is busy.

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

Libraries and assets used:

| Item | License | Link |
| --- | --- | --- |
| [PySide6](https://doc.qt.io/qtforpython-6/) | LGPL-3.0 (with the dynamic-linking exception used by PyInstaller) | https://www.qt.io/licensing |
| [Material Symbols Rounded](https://github.com/google/material-design-icons) | Apache License 2.0 | https://github.com/google/material-design-icons/blob/master/LICENSE |
| [pyperclip](https://pypi.org/project/pyperclip/) | BSD-3-Clause | https://github.com/asweigart/pyperclip/blob/master/LICENSE.txt |

LGPL-3.0 and Apache-2.0 are both compatible with MIT redistribution as
long as we keep the upstream attribution (see [LICENSE](LICENSE)).
