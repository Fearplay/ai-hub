# AI Hub (česky)

> Anglickou verzi najdeš v [README.md](README.md). Tato česká verze drží
> obě poznámky (English / Czech) v synchronizaci pro uživatele, kteří
> nečtou anglicky.

> **Postaveno s [Cursor](https://cursor.com)** - AI editor, ve kterém celý
> tento projekt vznikl (architektura, sekce, AI pipelines, build skript).

Desktopový AI Hub postavený v Pythonu s knihovnou
[PySide6](https://doc.qt.io/qtforpython-6/) (Qt 6 pro Python).
Tříslupcový layout: navigace v levém sidebaru, hlavní pracovní plocha ve
středu a kontextový panel vpravo. Sekce **AI Životopis / Kariéra**,
**AI LinkedIn Profile Builder**, **AI Finance**, **AI Hledání práce**
a **AI Právní asistent** jsou plně napojené na OpenAI / Anthropic;
ostatní sekce jsou postavené na stejné architektuře
a postupně se napojují.

Levý sidebar je teď **drag-and-drop přerovnatelný** - chytni malý úchyt
napravo u kterékoli AI sekce a pusť ji tam, kam chceš. Pořadí se ukládá
do `~/AI Hub/settings.json`, takže layout přežije restart. Sekundární
skupina (Historie / Oblíbené / Nastavení) zůstává pevně pod
oddělovačem.

## Požadavky

- Python 3.10+
- PySide6 >= 6.7.0 (Qt 6.x; runtime se vozí s balíčkem - žádné extra SDK)
- Alespoň jeden API klíč nastavený v sekci **Nastavení**:
  - **OpenAI** (`sk-…`) nebo **Anthropic** (`sk-ant-…`)
  - **GitHub** personal access token (volitelný, zvedne rate-limit pro AI Career)

> Žádné Flutter SDK, Qt SDK ani Visual Studio C++ není potřeba. Build
> běží přes `pyinstaller` (volaný z `build_exe.bat`), který si vystačí
> s čistým Pythonem na PATH.

## Instalace (vývoj)

```bash
python -m venv .venv
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Vývojové spuštění

```bash
py main.py            # Windows
python main.py        # macOS / Linux
```

Upload zóny v **AI Právní asistent**, **AI Životopis / Kariéra**,
**AI LinkedIn Profile Builder** i **AI Doc Assistant** sdílí jednu
komponentu (`src/components/file_drop_zone.py`), která:

* Vykreslí zónu s čárkovaným okrajem a výrazným call-to-action
  „Klikni a vyber soubor" - kliknutí otevře nativní file picker. Žádné
  samostatné "Upload" tlačítko už není - čárkovaná zóna *je* tlačítko,
  takže UI nemá dva redundantní způsoby jak udělat totéž.
* Pod zónou vždy vykreslí tlačítko **Vložit cestu**. Na Windows si
  v Průzkumníku dáš `Shift+Pravý klik` na soubor → *Kopírovat jako
  cestu*, klikneš na tlačítko a soubor se ihned načte.
* Přijímá skutečný **OS drag-and-drop** díky Qt `dragEnterEvent` /
  `dropEvent` - soubor přetažený z Průzkumníku / Finderu / Files se
  naplní okamžitě.
* Přijímá **PDF / DOCX / HTML / HTM / TXT / MD** - extrahovaný text je
  to, co krmí AI prompty v **AI Právním asistentovi**, **AI Career** a
  podobně.

Práce se schránkou je centralizovaná v `src/services/clipboard.py` -
synchronní obálka nad knihovnou
[pyperclip](https://pypi.org/project/pyperclip/) (s fallbacky
`win32clipboard` / `pbcopy` / `xclip` / `tkinter`), takže Copy / Paste
tlačítka jsou robustní bez ohledu na stav Qt session.

## Build .exe (Windows)

Pro distribuci na Windows je v rootu repa skript [`build_exe.bat`](build_exe.bat). Dvojklikem vyrobí jediný soubor `dist\AIHub.exe`, který si uživatel pustí na čistém PC bez Pythonu / venv / SDK.

Co skript dělá:

1. Pokud chybí Python na PATH, zkusí ho doinstalovat přes `winget install -e --id Python.Python.3.13`. Když ani winget není k dispozici, vypíše odkaz na python.org a skončí.
2. Pokud neexistuje `.venv\`, vytvoří ho.
3. Aktivuje venv a nainstaluje `requirements.txt` + `pyinstaller`.
4. Pustí `pyinstaller --onefile --windowed --name AIHub` (s vloženým
   subsetem fontu **Material Symbols Rounded** z `assets\fonts\`) a
   vyrobí `dist\AIHub.exe`.

Použití:

```bat
build_exe.bat            REM standardní build (skip když je exe novější než zdrojáky)
build_exe.bat --force    REM vždy rebuild i když nic nezměnilo
```

Trade-off: PyInstaller zabalí PySide6 (Qt 6 runtime) přímo do .exe -
žádné Flutter SDK, žádné Qt SDK, žádný Visual Studio C++. OS
drag-and-drop souborů **funguje**, protože ho Qt obsluhuje nativně.

Cursor pravidlo [`.cursor/rules/build-exe.mdc`](.cursor/rules/build-exe.mdc) zajišťuje, že agent spustí `build_exe.bat` na konci každého úkolu, takže `dist\AIHub.exe` zůstává v souladu se zdrojáky.

### Pro spoluvývojáře (úplně stejné prostředí, žádné kopírování)

Ať máte oba na stejném prostředí, **nesdílí se** ručně žádný build artefakt
(`AIHub.spec`, `.venv\`, `dist\`, `build\` - všechny jsou v
[.gitignore](.gitignore)). Druhý vývojář dostane identické prostředí takhle:

1. `git clone <repo-url>`
2. `cd ai-hub`
3. `build_exe.bat` (jeden klik)

Skript:

- Nainstaluje Python přes `winget`, pokud chybí.
- Vyrobí lokální `.venv\` a nainstaluje `requirements.txt` přesně tak, jak
  vidíš ty (commit-pinned).
- `pyinstaller` si vygeneruje **vlastní** `AIHub.spec` (ten u tebe je
  jen artefakt z poslední buildovky, nepatří do gitu).
- Vyrobí `dist\AIHub.exe`.

Pokud chceš jen pustit dev mód (bez exe), stačí krok 1-2 plus
`pip install -r requirements.txt` a `py main.py` - viz
*[Instalace (vývoj)](#instalace-vývoj)*.

## API klíče a kde se ukládají

Sekce **Nastavení** (v sidebaru pod oddělovačem) umožní:

- vybrat AI providera (**OpenAI** / **Anthropic**) a model (default `gpt-5.4-mini` / `claude-haiku-4-5`),
- uložit a smazat API klíče (OpenAI / Anthropic / GitHub),
- přepnout, zda se mají automaticky ptát doplňující otázky před spuštěním pipeline,
- zapnout / vypnout živá tržní data v AI Finance,
- otevřít **Debug logy** (zobrazit / zkopírovat / vymazat / otevřít složku).

Klíče se neukládají na disk v plain textu. Aplikace je pošle do nativního úložiště OS přes balíček [`keyring`](https://pypi.org/project/keyring/):

| OS | Backend |
| --- | --- |
| Windows | Credential Manager |
| macOS | Keychain |
| Linux | Secret Service / KWallet (pokud je nainstalovaný) |

Když `keyring` nemá dostupný backend (typicky headless Linux bez `gnome-keyring`), Settings UI se sám přepne do read-only režimu a vysvětlí, co je potřeba doinstalovat.

### HTTPS přes systémové úložiště certifikátů

Každé volání OpenAI / Anthropic / GitHubu jde přes `httpx`, který ve
výchozím stavu ověřuje certifikáty proti vendorovanému `certifi` CA
balíku. Ve firemních / školních sítích (Zscaler, Netskope, antivirový
MITM, vlastní interní root) je řetězec uložený jen v **OS** úložišti,
ne v `certifi`, a requesty padají na `SSL: CERTIFICATE_VERIFY_FAILED`.
Aby HTTPS na takových strojích fungovalo bez ruční konfigurace, volá
`main.py` jako úplně první runtime příkaz
[`truststore.inject_into_ssl()`](https://truststore.readthedocs.io/),
který přepojí Python `ssl.SSLContext` na nativní úložiště:

| OS | Backend |
| --- | --- |
| Windows | CryptoAPI (Trusted Root Certification Authorities) |
| macOS | Security framework |
| Linux | OpenSSL systémové rooty |

`truststore` je přidán do `requirements.txt` a do .exe se dostává přes
`--collect-submodules truststore` v `build_exe.bat`. Žádný kód v
sekcích / knihovnách `inject_into_ssl()` nevolá - dle upstream
upozornění to smí jen entry-point aplikace.

### Web search v chatu (opt-in)

OpenAI (`web_search_preview`) i Anthropic (`web_search_20250305`) mají
vestavěné nástroje na webové vyhledávání. Můžou tak odpovědět třeba na
„kolik dneska zavřel S&P 500" aniž bychom kamkoli posílali tvoje
osobní údaje. Zapni je v **Nastavení -> Povolit vyhledávání na webu v
AI chatu** - defaultně je to vypnuté, protože dohledání stojí extra
tokeny. K providerovi se dostane jenom tvůj dotaz, nic víc (žádná IP,
zařízení ani historie prohlížení).

Stejný přepínač najdeš i v chat liště AI Finance jako pill „Web: ZAP /
VYP", abys ho mohl(a) přepínat za běhu bez opouštění sekce.

### Živá tržní data (opt-in, defaultně zapnuto)

AI Finance kreslí pruh živých tickerů přes
[`yfinance`](https://pypi.org/project/yfinance/). Volá jen veřejné
endpointy Yahoo Finance - žádný API klíč, žádný účet, žádná
identifikace uživatele. Defaultní symboly jsou S&P 500 (`^GSPC`),
NASDAQ (`^IXIC`), DOW JONES (`^DJI`), BTC/USD (`BTC-USD`) a EUR/CZK
(`EURCZK=X`). Výsledky cachujeme v paměti 60 sekund. **Nastavení -> Živá
tržní data** vypne stahování úplně a pravý panel přepne na mock
tickery.

### Debug logy

Když nějaké kliknutí "neudělá nic" (přepnutí jazyka / barvy, mode tab,
uložení), aplikace si o tom vede stručný log soubor:

- Cesta: `~/AI Hub/logs/app.log` (rotace na 1 MB, max 4 soubory)
- Otevři **Nastavení -> Debug logy -> Zobrazit logy** v aplikaci. Dá se
  obnovit, zkopírovat do schránky, otevřít složku v Průzkumníku nebo
  vymazat.
- Prohlížeč v aplikaci obarvuje řádky podle úrovně (červená pro
  `ERROR`, oranžová pro `WARNING`, azurová pro `DEBUG`, default pro
  `INFO`, tučně červená pro `CRITICAL`). Soubor na disku zůstává
  obyčejný text - barvy jsou jenom v UI. Stránka Nastavení používá
  celou šířku okna, aby se zarovnané sloupce nelámaly.
- Logy se renderují v `QPlainTextEdit` s vlastním `QSyntaxHighlighter`,
  takže myší přetáhneš označení přes víc řádků a stiskneš `Ctrl+C`,
  nebo nahoře klikneš **Zkopírovat** a do schránky se přesune celý
  soubor. Kopírování jde přes OS schránku (pyperclip) pro
  cross-platformní spolehlivost.
- Žádná osobní data se do logu nezapisují - jenom co kdo kliknul, co se
  podařilo a stack trace případné chyby.

Od května 2026 je log strukturovaný do **sloupcového formátu**, takže
se v něm dá zorientovat na první pohled:

```
2026-05-09 19:32:14.501 | INFO  | ai_career.pipeline       | run_full_analysis_start  | url=… kind=cv
2026-05-09 19:32:14.620 | INFO  | ai_career.pipeline       | activity                  | text="Fetching job posting…"
2026-05-09 19:32:18.044 | INFO  | ai_career.pipeline       | run_full_analysis_done    | duration_ms=3543 status=ok
2026-05-09 19:32:18.060 | ERROR | ai_career.tab_documents  | refine_failed             | reason=ProviderError trace=…
```

Co je nového:

- `@logger_service.timed_call("…")` se dá pověsit na jakoukoli funkci
  a logger sám měří dobu běhu a zaznamená `duration_ms`.
- `logger_service.log_state("…", state, fields=("…",))` je standardní
  způsob, jak zalogovat snapshot sekce ve chvíli, kdy se tam zrovna něco
  děje (např. před spuštěním pipeline).
- Skoro všechny `except: pass` výjimky v sekcích `ai_career` a
  `ai_linkedin` byly nahrazeny voláním `logger_service.log_exception(...)`,
  takže žádná chyba v UI nebo workeru už nemizí potichu.

Detaily k novým pravidlům jsou ve workspace pravidlech
[`.cursor/rules/sections.mdc`](.cursor/rules/sections.mdc).

## Struktura projektu

```
ai-hub/
├── main.py                       # entry point
├── requirements.txt
├── README.md                     # angličtina
├── README.cs.md                  # tento soubor (čeština)
├── CONTRIBUTING.md
├── LICENSE
├── .gitignore
├── assets/
│   └── fonts/                     # vložený subset Material Symbols Rounded + codepoints
└── src/
    ├── theme.py                  # barvy a designové tokeny (dark + light)
    ├── app.py                    # AIHubApp - stav, layout, routing (sekce nezná jménem)
    ├── i18n.py                   # globální EN/CS překlady + t(key, lang)
    ├── qt/                        # PySide6 stavební bloky
    │   ├── theme.py              # QSS emitter + rgba helper
    │   ├── icons.py              # loader fontu Material Symbols Rounded + codepointy
    │   ├── widgets.py            # Card / IconLabel / ElidedLabel / typografie / tlačítka / Pill
    │   ├── effects.py            # drop shadow + opacity helpery
    │   ├── markdown.py           # bold-spans pro plain QLabel
    │   ├── dialog.py             # BaseDialog (themed modal scaffold)
    │   ├── runtime.py             # cross-thread UI dispatcher (worker → GUI)
    │   └── window_chrome.py      # Win32 DWM helper - obarví OS title bar podle theme
    ├── components/               # sdílené UI prvky (PySide6)
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
    │   ├── file_drop_zone.py     # sdílený upload (skutečný drag-drop + klik + paste-path)
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
    │   ├── store.py               # JSON-backed history & run output paths
    │   └── logger.py              # rotující debug log do ~/AI Hub/logs/app.log
    ├── sections/                 # FEATURE FOLDERS - 1 složka = 1 položka v sidebaru
    │   ├── __init__.py           # auto-discovery (PRIMARY + SECONDARY skupina)
    │   ├── _base.py              # Section dataclass (s nav_group)
    │   ├── SECTION_TEMPLATE/     # šablona pro novou sekci (READ ME)
    │   ├── dashboard/
    │   ├── ai_career/            # plně napojené na AI (HR expert, CV / cover letter)
    │   ├── ai_linkedin/          # plně napojené (LinkedIn Profile Builder + content)
    │   ├── ai_legal/              # AI-napojený chat (multi-formát upload + 4 quick actions)
    │   ├── ai_business/          # placeholder
    │   ├── ai_marketing/         # postavené podle návrhu (mock UI)
    │   ├── ai_finance/           # plně napojené (rozpočty / spoření / investice / analýza / daně / pojištění / kalkulačky)
    │   ├── ai_jobs/              # plně napojené AI Hledání práce (12-krokový formulář, web-search discovery + ověření URL + per-position match scoring + skill gap analýza)
    │   ├── ai_study/             # placeholder
    │   ├── ai_documents/         # placeholder
    │   ├── ai_doc_assistant/     # AI asistent na PDF / DOCX (summary / Q&A / rewrite / extract)
    │   ├── history/              # placeholder (secondary nav)
    │   ├── favorites/            # placeholder (secondary nav)
    │   └── settings/             # API klíče, provider, obecné, debug logy (secondary nav)
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
- Přepínač světlý / tmavý režim - **Windows OS title bar** (proužek
  s X / minimalizovat / maximalizovat a názvem appky) se přebarví
  podle aktivního theme přes DWM API, takže v dark módu už nepřežívá
  bílý pruh nad tmavým sidebarem (`src/qt/window_chrome.py`, na macOS /
  Linuxu nedělá nic).
- **Rychlé přepnutí theme + jazyka** - kliknutí na pill v sidebaru
  jenom znovu aplikuje globální QSS, přestaví sidebar a přestaví
  **jenom** aktivní sekci (ostatní si nový jazyk vyzvednou až při
  příštím kliknutí). Celé okno se už nepřebudovává od nuly, takže
  bývalá ~3sekundová pauza na sekci AI Career je pryč.
- **Nastavení** - API klíče (OpenAI / Anthropic / GitHub) v OS keystore, výběr providera + modelu, přepínače pro doplňující otázky a živá tržní data, debug logy
- **AI Životopis / Kariéra** - dva režimy přepínatelné v hlavičce sekce:
  - **Chat** (Verze B) - konverzační HR asistent, který si můžeš zeptat na cokoli k roli, životopisu, motivačnímu dopisu nebo přípravě na pohovor; do bubliny se dají připojit dokumenty (PDF / DOCX / TXT / MD / HTML) a kontext se přenáší do dalších otázek.
  - **Formulářový režim** (Verze A) - 4 stage taby (Setup → Match → Documents → History):
    - scrape inzerátu z URL nebo paste textu
    - upload životopisu (PDF / DOCX / TXT / HTML), volitelně LinkedIn export
    - GitHub URL s automatickým fetchem veřejných repos
    - 3 strukturované LLM kroky (Candidate / JobSpec / MatchAnalysis) + per-doc generátory (Tailored CV, Modern CV, Cover Letter, Match Report, Interview Prep, Skill Gap, Evidence)
    - inline refine ("Problem 1, Problem 2 …" → AI revize)
    - export do MD / HTML / DOCX / PDF (PDF přes Playwright když je dostupné, jinak `reportlab` fallback) a uložení kompletní analýzy do `outputs/ai_career/<role>-<timestamp>/` (každý "Save complete analysis" jde do **nové** složky s novým časem); odkazy `[label](url)` a holé URL se v PDF i HTML renderují jako kliky a z print stylu se odstranily efekty (text-shadow / stroke / fill-color), které kazily kontrast a označování textu
  - HR-expert system prompt s no-hallucination klauzulí, REORDER NEVER DELETE, CEFR-only, ATS pravidly atd.
- **AI LinkedIn Profile Builder** - kompletní pipeline pro generování / přepis LinkedIn profilu:
  - **Setup** - jméno, město, jazyk profilu (EN/CS), tone (warm / sharp / executive / casual), cílová role, target jobs (URL nebo text), CV / LinkedIn export upload, GitHub URL, do-not-mention seznam (témata, která AI nesmí zmínit) a pin / preferred sekce
  - **Sections** - výběr sekcí, které se mají vygenerovat (Headline, About, Experience, Education, Skills, Featured, Projects, Services, Courses, Recommendations, Posts, Messages, …); každá sekce může spustit svou pipeline samostatně nebo jednorázově běží **Run full profile build**
  - 1 strukturovaný LLM krok pro celkový profil + per-section follow-up calls (každý drží schéma a HR / brand pravidla)
  - **Anti-cringe** filtr (zakázaný buzzword glossary, no humble-bragging) přímo v system promptech
  - **Profile Completeness Checklist** s prioritami (must-have / nice-to-have / advanced) a celkovým profile score 0-100
  - **Output** tab - náhled per sekce + tlačítka Copy, Refine ("Problem 1 …"), Regenerate
  - Save complete LinkedIn package → `outputs/ai_linkedin/<handle>-<timestamp>/full_linkedin_profile.html` + jednotlivé sekce v MD / TXT / DOCX
  - EN/CS strings, doplňující otázky (clarifying questions) když chybí signál pro některou sekci
- **AI Finance** - opatrný osobní finanční asistent bez halucinací s osmi záložkami:
  - **Chat** - libovolné dotazy. Úvodní bublina ukáže tvůj poslední rozpočet (donut + rozpis) až poté, co si ho v záložce **Rozpočet** sestavíš; do té doby chat startuje s čistým pozdravem. Quick-action chipy navigují do strukturovaných záložek a **flow-wrap** se přelamují, takže nepřetékají v úzkých oknech.
  - **Rozpočet** - vyber metodu (`50/30/20`, `60/20/20`, `70/20/10`, zero-based, vlastní), zadej příjem + esenciály + cíle. Získáš strukturovaný `BudgetPlan` (cachovaný JSON) + donut, tabulku kategorií, upozornění a další kroky.
  - **Investice** - vrátí tři vzdělávací scénáře (Konzervativní / Vyvážený / Růstový) s alokací podle tříd aktiv a projektovanou hodnotou pro zvolený horizont. Nikdy nedoporučujeme konkrétní akcii ani fond.
  - **Analýza** - přetáhni CSV / PDF výpis z banky (parsuje se lokálně přes `src/services/file_parser.py`); asistent rozčlení výdaje podle kategorií, vyznačí pravidelné platby, top odlivy a navrhne, kde ušetřit.
  - **Daně** - checklist podle země + statusu, termíny, dokumenty k přípravě + zřetelné upozornění „nejsem licencovaný daňový poradce".
  - **Pojištění** - projde stávající smlouvy, vyznačí mezery / duplikace a doporučí další kroky.
  - **Kalkulačky** - šest čistě klientských kalkulaček (složené úročení, splátka hypotéky, bonita půjčky, důchodový plán, cíl spoření, převodník měn). Měna pohání živé FX přes službu `market_data`.
  - **Šablony** - čtyři statické šablonové karty z původního mock layoutu.
  - **Pravý kontextový panel** - **živý, uživatelem editovatelný přehled trhů** přes [`yfinance`](https://pypi.org/project/yfinance/) (free, veřejné Yahoo Finance endpointy; **žádný API klíč, účet ani identifikace uživatele**). Karta startuje s `^GSPC`, `^IXIC`, `^DJI`, `BTC-USD`, `EURCZK=X` a má tlačítko **Upravit** - dialog umožní přidat / odebrat tickery (libovolný Yahoo symbol) a seznam se ukládá do `~/AI Hub/settings.json`. Karty „Nedávné analýzy" a „Tip dne" zůstávají prázdné, dokud nespustíš reálnou pipeline; nikdy nezobrazují vymyšlená čísla.
  - **Empty-by-default UX** - Rozpočet / Investice / Analýza / Daně / Pojištění startují prázdné a strukturované karty se vykreslí až po kliknutí na primární CTA. Dvousloupcový layout (formulář / výsledek) se v úzkých oknech přepne do jednoho sloupce a quick-action chipy v chatu se přelamují na další řádek místo toho, aby přetekly mimo obrazovku.
- **AI Hledání práce** - hledá aktivně otevřené pozice na webu a porovnává je s tvým profilem:
  - **12-krokový formulář** (záložka Nastavení): klíčová slova role, profil (CV / bio / LinkedIn URL), lokalita (preset nebo vlastní), technologie + seniorita (Junior / Medior / Senior / Lead), exclusion list (slova / firmy / lokality / typy práce), výběr zdrojů (~70 portálů ve skupinách Globální / Remote / Evropa / CZ-SK / Tech-Startup / Freelance / Doporučené + textarea s vlastními URL - včetně českých specialistů jako JenPrace.cz / IT.jobs.cz / Pracomat / EasyJobs.cz / WTTJ Czechia, polských Pracuj.pl + JustJoin.IT, US Dice / Built In / The Muse, AT karriere.at, UK Reed / TotalJobs, ryze remote JustRemote / NoDesk / Jobspresso / 4 Day Week, freelance Arc.dev / Gun.io / Guru), stáří nabídky (Cokoli / 24h / 3d / 7d / 14d / 30d) s přepínači "ověřit odkazy" a "zobrazit i nabídky bez data", forma práce + úvazek (HPP / IČO / kontrakt / DPP-DPČ / stáž / freelance) + počet výsledků, režim hledání (Přesné / Chytré / Široké / Kariérní objevování), minimální plat + měna + jazyk výstupu (Auto / EN / CZ), předběžný souhrn s tlačítkem Hledat + sekundárními akcemi (Uložit jako šablonu / Vymazat / Načíst poslední), a seznam uložených profilů s akcemi (Spustit znovu / Upravit / Duplikovat / Smazat).
  - **Cíl = aktivní nabídky, over-fetch + top-up** - počet výsledků je počet pozic, na které **se opravdu dá přihlásit**, ne "co AI vrátila". Na pozadí discovery sahá 2x víc kandidátů (max 40), každý URL se ověří, a pokud po ověření zbývá málo aktivních, automaticky doběhne další discovery pass (s už viděnými URL na blacklistu v promptu). Výsledek: když si řekneš o 15, dostaneš až 15 použitelných plus malou sekci „Uzavřené nabídky" pro kontrolu detekce.
  - **Pětifázová pipeline**: (1) **discovery** s vestavěným web search a bohatým kontextem (režim, exclusion, stáří, zdroje, plat, případně seznam URL k vynechání pro top-up), (2) striktní JSON **extrakce** do `JOB_LISTINGS_SCHEMA` (název / firma / lokalita / vlozeno / ISO datum / plat / typ úvazku / shrnutí / URL / zdroj / forma práce), (3) **ověření URL** přes shared `job_scraper` (httpx + Playwright fallback - nabídky, které vrátí HTTP 404 / 410, přesměrují na placeholder „Stránka neexistuje", nebo se stránka načte ale obsahuje frázi typu „Už nepřijímá žádosti" / „No longer accepting applications" / „Tahle nabídka už je pryč" / „Nabídka není up-to-date", zůstanou viditelné s červeným odznakem **„Už nenabírá"**, jehož tooltip ukazuje konkrétní zachycenou frázi nebo HTTP status, takže můžeš detekci ověřit prokliknutím; zahazují se jen tvrdé pády scraperu - DNS / SSL / firewall), (4) **per-position match scoring** paralelně (`MATCH_SCHEMA`: shoda v %, sedící / chybějící skills, doporučení AI - skóruje se jen aktivní pozice, na uzavřené se neutrácí tokeny), (5) **agregovaná skill gap analýza** (`SKILL_GAP_SCHEMA`: nejčastější požadavky s počty, tvé silné stránky, chybějící skills, 1-6 konkrétních doporučení). Pasy 4 + 5 se automaticky přeskakují, pokud uživatel nedodal žádný profil.
  - **Lean Výsledky tab** s malou "Shoda XX %" pillou na kartě (zelená / žlutá / červená pásma) plus chip pro plat + úvazek + forma práce. Per-position chipy a doporučení AI se renderují **hlavně do ukládaného HTML**, aby zůstal seznam na obrazovce přehledný.
  - **Skill gap záložka** s top požadavky, silnými stránkami, chybějícími skills a doporučeními z Passu 5.
  - **Uložené profily hledání** v `~/AI Hub/jobs_profiles.json` - jedno-klikové spuštění, edit, duplikování, smazání. Žádná nová dependency, žádný nový secret.
  - **Bohaté HTML** (`Uložit jako HTML`) s match pillou, chip bloky sedí / chybí, doporučením u každé nabídky, samostatnou sekcí „Uzavřené nabídky" pro pozice, které už nenabírají, a kompletní skill gap sekcí. Každé uložení jde do nové složky `outputs/ai_jobs/<dotaz>-search-<timestamp>/` a registruje se v globálním `~/AI Hub/history.json`.
  - **Activity badge** (pravý kontextový panel) odráží každou fázi pipeline (`searching`, `extracting`, `verifying`, `scoring`, `gap_analysis`, `saving`, `ready`, `error`) plus quick action "Otevřít skill gap" který skočí přímo do nové záložky.
- **AI Marketing** - postavený podle dodaného návrhu (chat s "Instagram příspěvkem", phone mockup, brief panel)
- **AI Právní asistent** - plně AI-napojený chat s právním dokumentem:
  - **Multi-formát upload** - přetáhni `PDF`, `DOCX`, `HTML`, `TXT` (nebo `MD`) dokument do pravého panelu; tělo textu krmí prompty, z počítače odchází jen extrahovaný plain text.
  - **Čtyři quick-action tlačítka** - Shrnout / Najít rizika / Vysvětlit právní pojmy / Navrhnout úpravy - každé otevře specializovaný prompt a streamuje odpověď zpátky do chatu. Volné psaní v inputu funguje stejně.
  - **Disclaimer „nejsem advokát"** - inline banner pod hlavičkou připomíná, že asistent nenahrazuje právní poradenství; každá delší odpověď to znovu zmíní běžným jazykem.
  - **Kompaktní hlavička** - sekce Legal vypíná koncová tlačítka *Jak to použít* / `…` a používá užší top bar, aby chat měl víc vertikálního prostoru; ostatní sekce si zachovávají plnou hlavičku díky novým flagsům `show_help_button` / `show_menu_button` / `compact` v `src/components/header.py`.
- Pravý kontextový panel s **náklady relace** (calls / tokens / $) a aktivitou pipeline

## Co zatím **neumí** (záměrně)

- Streaming odpovědí v UI (první iterace volání blokuje s loaderem v context panelu)
- Multi-jazyčný OUTPUT_LANGUAGE per dokument (jeden run = jeden výstupní jazyk; řízeno globálním lang toggle)
- Skutečná persistence pro Favorites / History na úrovni celé appky (zatím per-section)
- AI v ostatních sekcích - architektura je připravená, sekce se postupně dopisují podle vzoru AI Career

## Postaveno s Cursorem

Tento repozitář vznikl v [Cursor](https://cursor.com) - AI editor, který
mi pomáhá psát kód, refaktorovat, přidávat sekce a držet pravidla projektu
(`.cursor/rules/`) v souladu se zbytkem kódu. Pravidla, podle kterých se
přidávají nové sekce, AI volání a buildy `.exe`, jsou v
[.cursor/rules/](.cursor/rules/). Když budeš chtít přidat vlastní sekci,
podívej se nejdřív do nich.

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

Použité knihovny a assety:

| Položka | Licence | Odkaz |
| --- | --- | --- |
| [PySide6](https://doc.qt.io/qtforpython-6/) | LGPL-3.0 (s výjimkou pro dynamické linkování, kterou PyInstaller používá) | https://www.qt.io/licensing |
| [Material Symbols Rounded](https://github.com/google/material-design-icons) | Apache License 2.0 | https://github.com/google/material-design-icons/blob/master/LICENSE |
| [pyperclip](https://pypi.org/project/pyperclip/) | BSD-3-Clause | https://github.com/asweigart/pyperclip/blob/master/LICENSE.txt |
| [yfinance](https://pypi.org/project/yfinance/) | Apache License 2.0 | https://github.com/ranaroussi/yfinance/blob/main/LICENSE.txt |

LGPL-3.0 i Apache-2.0 jsou s MIT redistribucí kompatibilní, dokud zachováme atribuci (viz [LICENSE](LICENSE)).
