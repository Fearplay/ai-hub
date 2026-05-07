# AI Hub

Desktopový AI Hub postavený v Pythonu s knihovnou [Flet](https://flet.dev). Tříslupcový layout: navigace v levém sidebaru, hlavní pracovní plocha ve středu a kontextový panel vpravo. Sekce **AI Životopis / Kariéra** je plně napojená na OpenAI / Anthropic; ostatní sekce jsou postavené na stejné architektuře a postupně se napojují.

## Požadavky

- Python 3.10+
- Flet >= 0.25.0 (testováno na 0.84.0)
- `flet-dropzone` (přidává OS drag-drop souborů — viz dále)
- API klíče (volitelné — bez nich jede Demo režim):
  - **OpenAI** (`sk-…`) nebo **Anthropic** (`sk-ant-…`) v sekci **Nastavení**
  - **GitHub** personal access token (volitelný, zvedne rate-limit pro AI Career)

### Pro jednorázový native build (kvůli `flet-dropzone`)

`flet-dropzone` integruje Flutter package `desktop_drop`, takže vyžaduje, aby si aplikace **jednou** sestavila vlastní native client. Bez buildu aplikace pojede dál, jen drag-drop nebude aktivní (viz *Runtime fallback* níže).

- **Flutter SDK** ≥ 3.22 — <https://docs.flutter.dev/get-started/install/windows>
- **Visual Studio 2022** s workloadem *Desktop development with C++* (potřebné pro Windows desktop build — MSVC + Windows 10/11 SDK)
- Po instalaci spusť `flutter doctor` a vyřeš případná chybějící „X" (typicky license agreement)

## Instalace

```bash
python -m venv .venv
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## První spuštění (jednorázové)

Sestavení vlastního clientu, který obsahuje `flet-dropzone`:

```bash
# Windows
py -m flet build windows -v

# Linux
flet build linux -v

# macOS
flet build macos -v
```

## Vývojové spuštění (denně)

Po prvním buildu:

```bash
py -m flet run
```

Hot-reload zachován. Drag-and-drop souborů z OS funguje v sekci **AI Právní asistent** a **AI Životopis / Kariéra**.

## Build .exe (Windows)

Pro distribuci na Windows je v rootu repa skript [`build_exe.bat`](build_exe.bat). Dvojklikem vyrobí jediný soubor `dist\AIHub.exe`, který si uživatel pustí na čistém PC bez Pythonu / venv / SDK.

Co skript dělá:

1. Pokud chybí Python na PATH, zkusí ho doinstalovat přes `winget install -e --id Python.Python.3.13`. Když ani winget není k dispozici, vypíše odkaz na python.org a skončí.
2. Pokud neexistuje `.venv\`, vytvoří ho.
3. Aktivuje venv a nainstaluje `requirements.txt` + `pyinstaller`.
4. Pustí `flet pack main.py --name AIHub` a vyrobí `dist\AIHub.exe`.

Použití:

```bat
build_exe.bat            REM standardní build (skip když je exe novější než zdrojáky)
build_exe.bat --force    REM vždy rebuild i když nic nezměnilo
```

Trade-off: `flet pack` (na rozdíl od `flet build windows`) **nepotřebuje Flutter SDK ani Visual Studio C++**, takže build funguje na čistém Windows. Cenou za to je, že drag-and-drop přes `flet-dropzone` v zabaleném exe nemusí fungovat - upload zóny ale vždy reagují na klik a otevřou nativní file picker.

Cursor pravidlo [`.cursor/rules/build-exe.mdc`](.cursor/rules/build-exe.mdc) zajišťuje, že agent spustí `build_exe.bat` na konci každého úkolu, takže `dist\AIHub.exe` zůstává v souladu se zdrojáky.

## API klíče a kde se ukládají

Sekce **Nastavení** (v sidebaru pod oddělovačem) umožní:

- vybrat AI providera (**OpenAI** / **Anthropic**) a model (default `gpt-5.4-mini` / `claude-haiku-4-5`),
- uložit a smazat API klíče (OpenAI / Anthropic / GitHub),
- nastavit globální flagy (Demo režim, doplňující otázky).

Klíče se neukládají na disk v plain textu. Aplikace je pošle do nativního úložiště OS přes balíček [`keyring`](https://pypi.org/project/keyring/):

| OS | Backend |
| --- | --- |
| Windows | Credential Manager |
| macOS | Keychain |
| Linux | Secret Service / KWallet (pokud je nainstalovaný) |

Když `keyring` nemá dostupný backend (typicky headless Linux bez `gnome-keyring`), Settings UI se sám přepne do read-only režimu a vysvětlí, co je potřeba doinstalovat.

### Demo režim (offline, bez tokenů)

Každá AI sekce má v Setupu tlačítko **Vyzkoušet ukázková data**, které celý workflow projde bez jediného volání providera. Vhodné pro screenshoty, demonstrace a první seznámení s appkou.

### Runtime fallback bez buildu

Pokud spustíš jen `python main.py` (nebo `py main.py`) bez `flet build`, aplikace funguje, jen `flet-dropzone` extension není napojená na native vrstvu — drop zóna v AI Právní asistent reaguje pouze na klik (otevře nativní file picker). Skutečný OS drag-drop ožije až po buildu.

## Struktura projektu

```
ai-hub/
├── main.py                       # entry point
├── requirements.txt
├── README.md
├── CONTRIBUTING.md
├── LICENSE
├── .gitignore
└── src/
    ├── theme.py                  # barvy a designové tokeny (dark + light)
    ├── app.py                    # AIHubApp - stav, layout, routing (sekce nezná jménem)
    ├── i18n.py                   # globální EN/CS překlady + t(key, lang)
    ├── components/               # sdílené UI prvky
    │   ├── sidebar.py            # iteruje registr sekcí, header / scroll / footer
    │   ├── nav_item.py
    │   ├── user_card.py
    │   ├── section_card.py
    │   ├── document_chip.py
    │   ├── header.py             # generický (icon, title, subtitle, ? button)
    │   ├── how_to_dialog.py      # generický modal "Jak používat asistenta"
    │   ├── tab_bar.py            # generický (list záložek, active index)
    │   ├── chat_message.py
    │   ├── chat_input.py
    │   ├── context_panel.py      # shell + helpery pro pravý panel
    │   ├── language_toggle.py    # přepínač EN / CS
    │   ├── theme_toggle.py       # přepínač dark / light
    │   └── placeholder.py        # výchozí "připravuje se" view
    ├── services/                 # SDÍLENÁ INFRASTRUKTURA - jediný vstup pro AI
    │   ├── secrets.py             # keyring wrapper (OS-native API key storage)
    │   ├── settings_store.py      # JSON preferences (provider, model, flagy)
    │   ├── ai_provider.py         # run(system, user, schema, ...) → OpenAI / Anthropic
    │   ├── cost_tracker.py        # session counter (calls / tokens / $)
    │   ├── job_scraper.py         # URL → job posting text
    │   ├── file_parser.py         # PDF / DOCX / TXT / HTML → plain text
    │   ├── github_client.py       # public profile + repo summary
    │   ├── exporter.py            # Markdown → MD / HTML / DOCX / PDF
    │   └── store.py               # JSON-backed history & run output paths
    ├── sections/                 # FEATURE FOLDERS - 1 složka = 1 položka v sidebaru
    │   ├── __init__.py           # auto-discovery (PRIMARY + SECONDARY skupina)
    │   ├── _base.py              # Section dataclass (s nav_group)
    │   ├── SECTION_TEMPLATE/     # šablona pro novou sekci (READ ME)
    │   ├── dashboard/
    │   ├── ai_career/            # plně napojené na AI (HR expert, CV / cover letter)
    │   ├── ai_legal/              # plně postavené (4 funkční taby + drag-drop)
    │   ├── ai_business/          # placeholder
    │   ├── ai_marketing/         # postavené podle návrhu (mock UI)
    │   ├── ai_finance/           # placeholder
    │   ├── ai_study/             # placeholder
    │   ├── ai_documents/         # placeholder
    │   ├── ai_doc_assistant/     # AI asistent na PDF / DOCX (summary / Q&A / rewrite / extract)
    │   ├── history/              # placeholder (secondary nav)
    │   ├── favorites/            # placeholder (secondary nav)
    │   └── settings/             # API klíče, provider, obecné (secondary nav)
    └── data/
        └── user.py               # globální mock (jenom přihlášený uživatel)
```

Každá složka v `src/sections/` má:

- `section.py` - registrace (`SECTION = Section(...)`)
- `view.py` - hlavní střední sloupec
- `strings.py` - EN + CS překlady té sekce
- `data.py` (volitelně) - mock data
- `context.py` (volitelně) - pravý kontextový panel

Adding a new section nikdy neotevírá `src/app.py` ani `src/components/sidebar.py`.
Detaily v [CONTRIBUTING.md](CONTRIBUTING.md) a v
[src/sections/SECTION_TEMPLATE/README.md](src/sections/SECTION_TEMPLATE/README.md).

## Co umí

- Tříslupcový layout, scrollovatelný sidebar (header / scroll / footer)
- **Přepínač jazyka** EN ↔ CS v sidebaru (default English, jak chtěl tým)
- Auto-discovery sekcí (primary + secondary skupina; History / Favorites / Settings v secondary)
- Přepínač světlý / tmavý režim
- **Nastavení** - API klíče (OpenAI / Anthropic / GitHub) v OS keystore, výběr providera + modelu, demo flagy
- **AI Životopis / Kariéra** - 4 stage taby (Setup → Match → Documents → History):
  - scrape inzerátu z URL nebo paste textu
  - drag-drop životopisu (PDF / DOCX / TXT / HTML), volitelně LinkedIn export
  - GitHub URL s automatickým fetchem veřejných repos
  - 3 strukturované LLM kroky (Candidate / JobSpec / MatchAnalysis) + per-doc generátory (Tailored CV, Modern CV, Cover Letter, Match Report, Interview Prep, Skill Gap, Evidence)
  - inline refine ("Problem 1, Problem 2 …" → AI revize)
  - export do MD / HTML / DOCX / PDF a uložení kompletní analýzy do `~/AI Hub/runs/<timestamp>/`
  - Demo režim (offline showcase)
  - HR-expert system prompt s no-hallucination klauzulí, REORDER NEVER DELETE, CEFR-only, ATS pravidly atd.
- **AI Marketing** - postavený podle dodaného návrhu (chat s "Instagram příspěvkem", phone mockup, brief panel)
- **AI Právní asistent** - 4 funkční taby (Chat, Analýza dokumentu, Návrhy dokumentů, Šablony), OS drag-drop PDF, mock LLM
- Pravý kontextový panel s **náklady relace** (calls / tokens / $) a aktivitou pipeline

## Co zatím **neumí** (záměrně)

- Streaming odpovědí v UI (první iterace volání blokuje s loaderem v context panelu)
- Multi-jazyčný OUTPUT_LANGUAGE per dokument (jeden run = jeden výstupní jazyk; řízeno globálním lang toggle)
- Skutečná persistence pro Favorites / History na úrovni celé appky (zatím per-section)
- AI v ostatních sekcích - architektura je připravená, sekce se postupně dopisují podle vzoru AI Career

## Contributors

Lidi, kteří se na projektu podílejí:

<table>
  <tr>
    <td align="center" width="120">
      <a href="https://github.com/Fearplay">
        <img src="https://github.com/Fearplay.png" width="80" alt="Fearplay" />
        <br />
        <sub><b>Fearplay</b></sub>
      </a>
      <br />
      <sub>autor & maintainer</sub>
    </td>
    <td align="center" width="120">
      <a href="https://github.com/lukasekcerny">
        <img src="https://github.com/lukasekcerny.png" width="80" alt="lukasekcerny" />
        <br />
        <sub><b>lukasekcerny</b></sub>
      </a>
      <br />
      <sub>spoluautor</sub>
    </td>
  </tr>
</table>

Až bude repo veřejné, půjde tuhle galerii vyměnit za auto-generovanou:

```markdown
<a href="https://github.com/Fearplay/ai-hub/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Fearplay/ai-hub" alt="Contributors" />
</a>
```

Chceš pomoct? Detaily workflow, pojmenování branch a commitů jsou v souboru [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

Tento projekt je licencován pod **MIT licencí** - viz soubor [LICENSE](LICENSE).

Použité knihovny:

| Knihovna | Licence | Odkaz |
| --- | --- | --- |
| [Flet](https://flet.dev) | Apache License 2.0 | https://github.com/flet-dev/flet/blob/main/LICENSE |

Apache 2.0 je s MIT plně kompatibilní, takže můžeme tento projekt distribuovat pod MIT, dokud zachováme atribuci původní knihovny (viz [LICENSE](LICENSE)).
