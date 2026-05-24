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
in the middle, and a context panel on the right. The default landing
view is the **Dashboard** - a navigation grid with one card per visible
AI module, so the user can jump straight into any assistant from a cold
launch. **AI CV / Career**, **AI LinkedIn Profile Builder**, **AI
Finance**, **AI Job Search**, and **AI Bug Report** are fully wired to
OpenAI / Anthropic (the new section also speaks the providers'
**vision** APIs so screenshots are processed alongside the text
prompt). The work-in-progress sections (AI Legal, AI Business, AI
Marketing, AI Study, AI Documents, AI Doc Assistant) are kept in the
repo so the architecture stays documented but are currently **hidden
from the sidebar** - see [Hidden UI](#hidden-ui) below to flip them
back on.

The left sidebar is **drag-and-drop reorderable** - grab the small grip
on the right of any primary AI section and drop it where you want. The
new order applies instantly (no restart, no language toggle). Order
persists in `~/AI Hub/settings.json` so your layout survives restarts.
The secondary group (**Dashboard** above **Settings**) stays pinned
below the divider; both are non-reorderable so the navigation grid and
the settings page are always one click away.

## Requirements

- Python 3.10+
- PySide6 >= 6.7.0 (Qt 6.x, ships its own Qt runtime - no extra SDK)
- At least one provider API key configured under **Settings**:
  - **OpenAI** (`sk-...`) or **Anthropic** (`sk-ant-...`)
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
**AI LinkedIn Profile Builder**, **AI Doc Assistant**, and **AI Bug
Report** all share one component (`src/components/file_drop_zone.py`)
that:

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
  and friends. The AI Bug Report section opts in to **image files**
  (PNG / JPG / WEBP / GIF / BMP / HEIC) and `.log` / `.json` on top of
  the shared list via a small local helper, so screenshots are sent to
  the model's vision API and raw logs are forwarded verbatim.

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
4. Runs `pyinstaller --onefile --windowed --name AIHub` and produces
   `dist\AIHub.exe`. Icons render via
   [QtAwesome](https://github.com/spyder-ide/qtawesome) (Material Design
   Icons 6); the icon fonts ship inside qtawesome's wheel and are
   pulled into the bundle automatically via `--collect-all qtawesome`.
   The app logo lives at `assets/logo.svg`, is used as the Qt window
   icon at runtime, and is bundled via `--add-data`.

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

### Production release

The deliverable for non-developer users is a **single self-contained
binary**: `dist\AIHub.exe`. To cut a release:

1. Pull the latest `main`.
2. Run `build_exe.bat --force` once - PyInstaller produces
   `dist\AIHub.exe` with PySide6 / Qt 6, the QtAwesome Material Design
   Icons 6 set, and every section module baked in. The repo-local
   `hooks\hook-src.sections.py` enumerates every `src\sections\<key>\`
   folder at build time and adds each `.py` file as a hidden import,
   so the runtime auto-discovery (`pkgutil.iter_modules`) finds every
   section folder when the .exe runs from a frozen bundle.
3. Hand the `.exe` to the user. First launch creates `~/AI Hub/`
   under the user's home directory, which is the **single** place the
   app writes anything outside the install folder:
   * `~/AI Hub/settings.json` - provider / model / sidebar order /
     opt-in flags,
   * `~/AI Hub/history.json` - run index for every section's saved
     outputs,
   * `~/AI Hub/logs/app.log` - rotating debug log (1 MB, 4 files),
   * `outputs/<section>/<run-slug>-<timestamp>/` - the actual run
     artefacts (DOCX, PDF, HTML, MD), created next to the .exe.

   Wiping `~/AI Hub/` is a hard reset; the .exe re-creates everything
   on the next launch.
4. API keys never leave the machine - they live in the OS native
   secret store (Windows Credential Manager / macOS Keychain / Linux
   Secret Service via [`keyring`](https://pypi.org/project/keyring/)).

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
- toggle the global "ask follow-up questions before running" preference,
- enable / disable live market data for AI Finance,
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

`yfinance` (used by **AI Finance** for live market data) talks to Yahoo
through `curl_cffi`, which uses libcurl's native TLS stack and does
**not** read the `ssl` module that `truststore` patched. To stop the
"curl: (60) SSL certificate problem: unable to get local issuer
certificate" failure on stock Windows Python, `main.py` also exports
`CURL_CA_BUNDLE` and `SSL_CERT_FILE` to the `certifi` Mozilla CA bundle.
The bundle ships inside the [`certifi`](https://pypi.org/project/certifi/)
wheel (Mozilla Public License 2.0) and is bundled into the .exe via
`--collect-data certifi` so `certifi.where()` resolves to a real PEM
file even when the app is frozen.

### Web search in chat (opt-in)

OpenAI (`web_search_preview`) and Anthropic (`web_search_20250305`) both
ship built-in web-search tools that can answer "what is today's S&P 500
close?" without us mailing user data anywhere. Flip them on under
**Settings -> Enable web search in AI chat** - the toggle is off by
default because the lookup costs extra tokens. Only the prompt you
typed reaches the provider; no IP, device fingerprint, or browsing
history is sent.

The same provider switch is exposed in the AI Finance chat composer as
a one-click pill ("Web: ON / OFF") so you can toggle it mid-conversation
without leaving the section.

### Live market data (opt-in default-on)

AI Finance renders a live ticker strip via
[`yfinance`](https://pypi.org/project/yfinance/). It hits public Yahoo
Finance endpoints only - no API key, no account, no user identification.
The default symbols are S&P 500 (`^GSPC`), NASDAQ (`^IXIC`), DOW JONES
(`^DJI`), BTC/USD (`BTC-USD`), and EUR/CZK (`EURCZK=X`). Results are
cached in-process for 60 seconds. The Markets card in the right
context panel has its own **Refresh** button next to *Edit* that
bypasses that throttle and triggers a fresh fetch; if Yahoo returns
no quotes (offline, proxy, dead symbol), the card now surfaces an
explicit error instead of staying stuck on the generic "no data" hint.
Flip **Settings -> Live market data** off to keep AI Finance fully
offline; the right-hand panel then falls back to its empty state.

**Stooq fallback (automatic).** When yfinance fails for a given symbol
(Yahoo TLS hiccup, the periodic endpoint shuffle, an empty history on
a fresh ticker), the service transparently retries via
[Stooq](https://stooq.com)'s key-free snapshot CSV
(`stooq.com/q/l/?s=<symbol>&f=sd2t2ohlcv&h&e=csv`). The fallback uses
only the standard-library `urllib`, maps Yahoo's symbols to Stooq's
convention internally (`^GSPC -> ^spx`, `BTC-USD -> btcusd`,
`AAPL -> aapl.us`, `EURCZK=X -> eurczk`, ...), and logs each fallback
as `stooq_fallback_used` in **Settings -> Debug logs**. The toggle
above still gates everything: turning **Live market data** off
disables both providers.

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
├── LICENSE
├── .gitignore
├── build_exe.bat                 # one-click Windows PyInstaller build
├── hooks/                        # repo-local PyInstaller hooks
│   ├── hook-src.sections.py      # enumerates every src/sections/<key>/*.py at build time
│   └── hook-src.services.py      # same idea for the shared service layer
└── src/
    ├── theme.py                  # design tokens (dark + light)
    ├── app.py                    # AIHubApp - state, layout, routing (no per-section knowledge)
    ├── i18n.py                   # global EN/CS strings + t(key, lang)
    ├── qt/                        # PySide6 building blocks
    │   ├── theme.py              # QSS emitter + rgba helper
    │   ├── icons.py              # QtAwesome-backed Icons.X registry (Material Design Icons 6)
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
    │   ├── ai_finance/           # fully wired (budgets / savings / investments / analysis / taxes / insurance / calculators)
    │   ├── ai_jobs/              # fully wired AI Job Search (12-step setup form, web-search discovery + URL verification + per-position match scoring + skill gap analysis)
    │   ├── ai_study/             # placeholder
    │   ├── ai_documents/         # placeholder
    │   ├── ai_doc_assistant/     # PDF / DOCX assistant (summary / Q&A / rewrite / extract)
    │   ├── ai_bug_report/         # fully wired (vision) - text / screenshots / logs -> Word bug report
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
Details in
[src/sections/SECTION_TEMPLATE/README.md](src/sections/SECTION_TEMPLATE/README.md).

## What it does

- Three-column layout, scrollable sidebar (header / scroll / footer).
- **Language toggle** EN <-> CS in the sidebar (default English, per the team).
- Section auto-discovery (primary + secondary; Settings is the only secondary entry).
- **Unified Demo mode** - every AI section ships a `Show demo data` entry under its header `...` menu. Picking it fills the section with curated offline payloads (AI Career persona, AI LinkedIn profile, AI Finance budget, AI Jobs result list, AI Bug Report sample, AI Doc Assistant sample, AI Legal sample) and lights up an orange `DEMO` pill in the header so it is always obvious which view is mock. Demo mode is **free** - the pipeline short-circuits every provider call, so users can showcase the app on a fresh install without an API key or a single token. Picking `Hide demo data` clears the curated state and restores the empty Setup tab.
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
- **Settings** - API keys (OpenAI / Anthropic / GitHub) in the OS keystore, provider + model picker, follow-up-question + market-data toggles, debug logs.
- **AI CV / Career** - two modes toggled in the section header:
  - **Chat** (Version B) - conversational HR assistant; you can attach documents (PDF / DOCX / TXT / MD / HTML) to a bubble and the context carries through follow-ups.
  - **Form mode** (Version A) - 4 stage tabs (Setup -> Match -> Documents -> History):
    - scrape the job posting from a URL or paste the text,
    - upload the resume (PDF / DOCX / TXT / HTML), optionally a LinkedIn export,
    - GitHub URL with automatic fetch of public repos,
    - 3 structured LLM steps (Candidate / JobSpec / MatchAnalysis) + per-document generators (Tailored CV, Modern CV, Cover Letter, Match Report, Interview Prep, Skill Gap, Evidence),
    - inline refine ("Problem 1, Problem 2..." -> AI revision),
    - export to MD / HTML / DOCX / PDF (with **clickable hyperlinks** in the PDF) and save the full analysis to `outputs/ai_career/<role>-<timestamp>/` (every "Save complete analysis" lands in a **fresh** timestamped folder).
  - HR-expert system prompt with no-hallucination clause, REORDER NEVER DELETE, CEFR-only, ATS rules, etc.
- **AI LinkedIn Profile Builder** - same two-mode shell (Chat / Builder), aimed at a complete LinkedIn rewrite:
  - **Setup** - target roles, audience (recruiter / peer / customer), tone (professional / friendly / bold / academic), output language (EN / CS), CV + LinkedIn export uploads, GitHub URL, free-form notes.
  - **Sections** picker - presets (essentials / full polish / job hunt / thought leadership) + 12-section grid with checkboxes (Headline, About, Experience, Education, Certifications, Skills, Featured, Projects, Services, Courses, Recommendations, Posts).
  - One LLM **profile-extraction** call followed by per-section generators that all reuse the cached profile JSON (cost-aware - never re-sends the raw CV text).
  - **Anti-cringe + no-hallucination** prompts; an unsupported-claims report flags any AI bullet that wasn't backed by source evidence.
  - **Profile completeness checklist** with priority levels (critical / important / nice to have) and a 0-100 profile score.
  - **Output** tab renders every generated section as a card (with copy-to-clipboard) + the checklist + the score.
  - Save the complete profile to `outputs/ai_linkedin/<target-role>-<timestamp>/` as MD per section, the comprehensive `full_linkedin_profile.html` summary, and a JSON snapshot for future runs.
- **AI Finance** - cautious, no-hallucination personal-finance assistant with eight tabs:
  - **Chat** - free-form questions. A greeting bubble shows your latest budget (donut + breakdown) once you build one in the Budget tab; before that, the chat starts from a clean greeting. Quick-action chips route to the structured tabs and **flow-wrap** so they don't overflow on narrow windows.
  - **Budget** - pick a method (`50/30/20`, `60/20/20`, `70/20/10`, zero-based, custom), enter income + essentials + goals, get a structured `BudgetPlan` JSON (cached) with donut chart, category table, warnings, and next-step suggestions. Below the result you also get a **savings plan** card (timeline of milestones + projected balance after 6 / 12 / 24 / 36 months built from `generate_savings_plan`) and an **Edit / refine** box that calls `edit_budget` when you want a quick "less restaurants, more 401k" tweak without re-typing the whole form.
  - **Investments** - returns three educational scenarios (Conservative / Moderate / Growth) with asset-class allocations rendered as **stacked allocation bars** plus a 12-month **projection sparkline** based on the scenario's expected annual return. Never names a specific stock or fund.
  - **Analysis** - drop a CSV / PDF bank statement (parsed locally via `src/services/file_parser.py`); the assistant categorises spend, renders a **horizontal bar chart** of categories (with recurring payments highlighted), flags recurring payments, lists top outflows, and proposes savings.
  - **Taxes** - country + filing-status checklist with a horizontal **deadline timeline** for the upcoming tax dates, documents to gather, and a "this is not licensed tax advice" disclaimer.
  - **Insurance** - reviews existing policies, renders a 3x3 **severity heatmap** of coverage gaps (critical / high / medium x policy type), flags duplicates, and suggests next steps.
  - **Calculators** - six pure-Python calculators (compound interest, mortgage payment, loan affordability, retirement planner, savings goal, currency converter). The currency converter pulls live FX via the `market_data` service.
  - **Templates** - lists every saved AI Finance run from `outputs/ai_finance/<run-slug>-<timestamp>/`. Each card has an **Open folder** action that pops the OS file browser straight to the PDFs / Markdown of that run; an empty-state card explains how to create your first one when there are no saved runs yet.
  - **Demo mode** - same shared `...` menu entry as every other AI section ("Show demo data" / "Hide demo data" + orange `DEMO` pill in the header). It swaps every pipeline call for a curated mock JSON (budget / analysis / investments / tax / insurance / savings plan / tip). The section has something to show on first launch - charts, tables, the right-hand AI tip - without spending any tokens. Picking "Hide demo data" goes straight back to live AI calls.
  - **AI Tip card** (right context panel) - dynamic, generated per analysis via `generate_tip` (cached in `STATE.tip` so flipping themes / languages does not re-spend tokens). The card has a **Generate new tip** button when you want a fresh take. Stays empty until your first analysis is done.
  - **Right-hand context panel** - **live, user-editable market overview** via [`yfinance`](https://pypi.org/project/yfinance/) (free, public Yahoo Finance endpoints; **no API key, no account, no user identification**). The card seeds with `^GSPC`, `^IXIC`, `^DJI`, `BTC-USD`, `EURCZK=X` and exposes an **Upravit / Edit** button - the dialog lets the user add / remove tickers (any Yahoo symbol) and persists the list to `~/AI Hub/settings.json`. The previous "unable to get local issuer certificate" SSL failure on stock Windows is gone now that the curl_cffi backend points at `certifi.where()`. The "Recent analyses" card stays empty until the user runs a real pipeline; nothing fakes the numbers.
  - **Empty-by-default UX** - Budget / Invest / Analysis / Taxes / Insurance start blank and only paint structured cards once you click their primary CTA. The two-column form / result layout collapses into a single column on narrow widths, and the chat quick-action chips wrap onto multiple rows instead of stretching off-screen.
- **AI Job Search** - find currently-open positions on the public web and score them against your profile:
  - **12-step setup form** (Setup tab): Role keywords, profile (CV / bio / LinkedIn URL), location preset or custom region, technologies + seniority pill (Junior / Medior / Senior / Lead), exclusions (keywords / companies / locations / work-type chips), sources picker (~70 portals grouped Global / Remote / Europe / CZ-SK / Tech-Startup / Freelance / Recommended + custom URLs textarea - including Czech specialists like JenPrace.cz / IT.jobs.cz / Pracomat / EasyJobs.cz / WTTJ Czechia, Polish Pracuj.pl + JustJoin.IT, US Dice / Built In / The Muse, AT karriere.at, UK Reed / TotalJobs, remote-only JustRemote / NoDesk / Jobspresso / 4 Day Week, freelance Arc.dev / Gun.io / Guru), posting age (Any / 24h / 3d / 7d / 14d / 30d) with "verify links" + "show postings without date" toggles, work-mode radios + contract chips (HPP / ICO / contract / DPP-DPC / internship / freelance) + result count, search mode (Exact / Smart / Broad / Career discovery), minimum salary + currency + output language (Auto / EN / CS), sticky footer Run button, secondary actions (Save as template / Clear / Load last search), and a Saved profiles list whose whole cards can rerun a saved search.
  - **Active-target over-fetch + top-up** - the result count is the number of **applicable** postings you want, not "raw URLs the AI returned". Internally the discovery pass over-fetches by 2x (capped at 40 candidates), every URL is verified, and a follow-up discovery pass automatically fires (with the already-seen URLs blacklisted in the prompt) if too many came back closed. Result: when you ask for 15, you get up to 15 you can actually apply to, plus a small "closed listings" section for transparency.
  - **Optional clarifying questions** - same shared modal as AI CV / Career and AI Bug Report. When **Settings -> Ask follow-up questions** is on, the pipeline runs a quick Pass 0 *before* discovery to ask 0-8 short questions about the brief (seniority mismatches, contradictory keywords, missing remote / salary preference, *"you mentioned Python but not how many years"*). Answers feed into the discovery, per-position scoring, and skill-gap prompts so the model stops guessing. The footer hosts a "Let the AI ask clarifying questions first" toggle and a one-line hint; flip it off when you want a one-click run.
  - **Five-pass pipeline**: (1) hosted **web-search discovery** with rich context (search mode, exclusions, age, sources, salary, optional already-seen-URL list for top-up), (2) strict-JSON **extraction** into `JOB_LISTINGS_SCHEMA` (title / company / location / posted / posted-ISO / salary text / contract type / summary / URL / source / work-mode), (3) **URL verification** through the shared `job_scraper` (httpx + Playwright fallback - listings that return HTTP 404 / 410, redirect to a "Stránka neexistuje" placeholder, or whose page still loads but says "No longer accepting applications" / "Už nepřijímá žádosti" / "Tahle nabídka už je pryč" / "Nabídka není up-to-date" stay visible with a red **"No longer hiring"** badge whose tooltip shows the matched phrase or HTTP status, so you can verify the detection by clicking through; only hard scrape crashes - DNS / SSL / firewall - are dropped), (4) **per-position match scoring** in parallel (`MATCH_SCHEMA`: match %, matched / missing skills, AI recommendation - active postings only, closed ones skip scoring to save tokens), (5) **aggregate skill-gap analysis** (`SKILL_GAP_SCHEMA`: most-requested skills with counts, your strong sides, missing skills, 1-6 actionable advice paragraphs). Pass 4 + 5 are skipped automatically when no profile material was provided.
  - **Lean Results tab** with a small "Match XX%" pill per card (green / amber / red bands) plus salary + contract + work-mode chips. Per-position chips and the AI recommendation paragraph render **primarily in the saved HTML** so the on-screen list stays scannable.
  - **Skill gap tab** with the top requirements, strong sides, missing skills, and advice paragraphs from Pass 5.
  - **Gated tabs + menu-only demo** - Results / Skill gap stay disabled until a run produced data. Curated demo results live in the header `...` menu instead of a visible demo button.
  - **Saved search profiles** persisted to `~/AI Hub/jobs_profiles.json` - one-click rerun, edit, duplicate, delete. No external dependency, no extra secret.
  - **Active-target ordering** - the search always tries to return the number of *applicable* openings you asked for. The pipeline starts strict (three top-up passes that respect your filters), and only falls back to a single relaxed broad pass (adjacent roles / nearby cities) if the strict run still cannot fill the quota. Relaxed hits are flagged with an amber **"Less relevant"** pill (in-app and in the HTML export) so you can tell at a glance which postings came from the broader search. Closed / inactive listings are still surfaced for transparency but never count toward the active target.
  - **Rich HTML export** (`Save as HTML`) with match pill, matched / missing chip blocks, recommendation per posting, the new "Less relevant" pill for relaxed-pass hits, a separate "Closed listings" section for postings that are no longer hiring, and the full skill-gap section. Each save lands in a fresh `outputs/ai_jobs/<query>-search-<timestamp>/` folder and registers in the global `~/AI Hub/history.json`.
  - **History restore** - clicking a saved search row loads its `summary.json` back into the app, repopulates Results / Skill gap, and lets you continue from the previous run.
  - **Activity badge** (right context panel) reflects every pipeline stage (`searching`, `extracting`, `verifying`, `scoring`, `gap_analysis`, `saving`, `ready`, `error`) plus a "Open skill gap" quick action that jumps straight to the new tab.
- **AI Bug Report** - turn a description, screenshots, and supporting docs / logs into a polished Word bug report:
  - **Vision input** - the combined drop zone accepts both screenshots (PNG / JPG / WEBP / GIF / BMP / HEIC) and text-like attachments (TXT / LOG / JSON / PDF / DOCX / MD / HTML). Screenshots are sent to the model via the providers' native vision APIs (`image_url` content blocks for OpenAI, `image` source blocks for Anthropic), text-like docs are parsed locally with `src/services/file_parser.py`.
  - **One or more bug scenarios** through a strict `BUG_REPORT_SCHEMA` (`title`, `summary`, `scenarios[]`, per-attachment summary, additional notes). The AI decides whether the inputs describe one bug or several distinct scenarios; Word export includes every detected scenario with its own severity, priority, environment, STR, expected vs actual, and notes.
  - **Optional clarifying questions** (same pattern as AI CV / Career and AI LinkedIn) - when **Settings -> Ask follow-up questions** is on, the section runs a fast Pass 0 that asks the model to list 0-8 short questions before the main bug-report call. The shared `src/components/followup_dialog.py` modal opens with chip-style options + an **Other...** free-text field per question; the answers are folded into the main prompt so the report no longer says *"(inferred)"* against facts the user could have just told the AI. A footer toggle ("Let the AI ask clarifying questions first") lets you flip the behaviour off per-section without leaving Settings.
  - **Gated preview** - Preview is disabled until a report exists. The input footer appears only on Input; Preview shows just the report actions (**Save as Word document**, **Open output folder**, **Back to Input**) and the generated content.
  - **Word export** via `python-docx` - the Preview actions write DOCX, Markdown, and `summary.json` to `outputs/ai_bug_report/<title-slug>-<timestamp>/` and register the run in `~/AI Hub/history.json`.
  - **History restore + menu-only demo** - clicking a saved bug-report row reloads it back into Preview. Demo data is available only from the header `...` menu, not as a persistent footer button.
- **AI Marketing** - built from the supplied design (chat with an "Instagram post", phone mockup, brief panel).
- **AI Legal assistant** - fully AI-wired chat with a legal document:
  - **Multi-format upload** - drag a `PDF`, `DOCX`, `HTML`, `TXT` (or `MD`) document onto the right-hand panel; the text body feeds the prompts, only the extracted plain text leaves your machine.
  - **Four quick-action chips** - Summarise / Find risks / Explain legal terms / Suggest changes - each opens a tailored prompt and streams the reply back into the chat. Plain typing in the input field also works.
  - **No-lawyer disclaimer** - inline banner under the header reminds the user the assistant does not replace legal advice; every long reply re-states it in plain language.
  - **Compact header** - the Legal section drops the trailing *How to use* / `…` buttons and uses a tighter top bar so the chat has more vertical space; other sections keep their full chrome via the new `show_help_button` / `show_menu_button` / `compact` flags on `src/components/header.py`.
- **Shared file-upload component** (`src/components/file_drop_zone.py`) - one place for click-to-browse, best-effort OS drag-and-drop, and clipboard-paste-path. AI Career, AI LinkedIn, and AI Legal all use it.
- Right context panel showing **session cost** (calls / tokens / $) and a real-time **Activity** badge that reflects the pipeline stage (`scraping`, `analyzing`, `generating`, `scoring`, `saving`, `error`, `ready`) - the badge updates from background worker threads via `REFS.request_context_refresh()` so the user never sees a stale "Ready" while the LLM is busy.

## Hidden UI

The sidebar currently only shows the five production-ready sections
(AI LinkedIn, AI CV / Career, AI Finance, AI Job Search, AI Bug Report)
plus **Settings** under the divider. Work-in-progress sections still live in
the repo but their `section.py` sets `hidden=True` so
`src/sections/__init__.py` skips them when building
`PRIMARY_SECTIONS` / `SECONDARY_SECTIONS`. They keep auto-discovering
and stay in `SECTIONS` / `SECTION_BY_KEY`, so deep-links / saved
sidebar orders that still reference them do not crash - they just are
not rendered.

| Section key | Folder | What it will become |
| --- | --- | --- |
| `ai_legal` | `src/sections/ai_legal/` | Multi-format upload + 4 quick-action legal chat (already wired to AI, hidden until copy is finalised). |
| `ai_business` | `src/sections/ai_business/` | Business-strategy / SaaS playbook helper. |
| `ai_marketing` | `src/sections/ai_marketing/` | Marketing copy / Instagram post generator (mock UI in place). |
| `ai_study` | `src/sections/ai_study/` | Study planner / flashcards. |
| `ai_documents` | `src/sections/ai_documents/` | Document generator placeholder. |
| `ai_doc_assistant` | `src/sections/ai_doc_assistant/` | PDF / DOCX summary + Q&A (Version B). |

To bring any of them back, open the section's `section.py` and set
`hidden=False` (or just delete the line). The `Section.hidden` field
defaults to `False`.

The sidebar also drops the **user card** ("Jan Novák" placeholder) for
the same reason - there is no real user identity yet. Re-add it in
`src/components/sidebar.py` once auth lands; the helper still lives in
`src/components/user_card.py`.

## Not yet (deliberately)

- Streaming responses in the UI (the first iteration blocks with a loader in the context panel).
- Multi-language `OUTPUT_LANGUAGE` per document (one run = one output language; driven by the global lang toggle).
- AI in the remaining sections - the architecture is ready, sections are filled in following the AI Career template.

## Built with Cursor

This codebase was authored in [Cursor](https://cursor.com), the AI
editor. Cursor agents follow rules in [.cursor/rules/](.cursor/rules/)
that codify how to add a new section, where AI provider calls live, how
to log debug events, and how the `.exe` is rebuilt at the end of every
task. If you plan to extend the project, read those rules first - they
are the source of truth for how new code is added.

## Licence

This project is licensed under the **MIT License** - see [LICENSE](LICENSE).

Libraries and assets used:

| Item | License | Link |
| --- | --- | --- |
| [PySide6](https://doc.qt.io/qtforpython-6/) | LGPL-3.0 (with the dynamic-linking exception used by PyInstaller) | https://www.qt.io/licensing |
| [QtAwesome](https://github.com/spyder-ide/qtawesome) | MIT License | https://github.com/spyder-ide/qtawesome/blob/master/LICENSE.txt |
| [Material Design Icons](https://pictogrammers.com/library/mdi/) (bundled inside QtAwesome) | Pictogrammers Free License (Apache-2.0 compatible) | https://pictogrammers.com/docs/general/license/ |
| [pyperclip](https://pypi.org/project/pyperclip/) | BSD-3-Clause | https://github.com/asweigart/pyperclip/blob/master/LICENSE.txt |
| [yfinance](https://pypi.org/project/yfinance/) | Apache License 2.0 | https://github.com/ranaroussi/yfinance/blob/main/LICENSE.txt |
| [truststore](https://pypi.org/project/truststore/) | MIT License | https://github.com/sethmlarson/truststore/blob/main/LICENSE |
| [certifi](https://pypi.org/project/certifi/) | MPL-2.0 (the bundled `cacert.pem` is Mozilla's CA store) | https://github.com/certifi/python-certifi/blob/master/LICENSE |

LGPL-3.0, Apache-2.0, and MPL-2.0 (only for the bundled CA list inside
`certifi`) are all compatible with MIT redistribution as long as we
keep the upstream attribution (see [LICENSE](LICENSE)).
