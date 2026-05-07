# AI Hub

UI mockup AI Hubu postavený v Pythonu s knihovnou [Flet](https://flet.dev). Tříslupcový layout: navigace v levém sidebaru, chat ve středu a kontextový panel vpravo. Bez AI logiky - pouze statický mockup s mock daty.

## Požadavky

- Python 3.10+
- Flet >= 0.25.0 (testováno na 0.84.0)

## Instalace

```bash
pip install -r requirements.txt
```

Doporučeno spustit ve virtuálním prostředí:

```bash
python -m venv .venv
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Spuštění

```bash
python main.py
```

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
    │   ├── sidebar.py            # iteruje registr sekcí
    │   ├── nav_item.py
    │   ├── user_card.py
    │   ├── section_card.py
    │   ├── document_chip.py
    │   ├── header.py             # generický (icon, title, subtitle)
    │   ├── tab_bar.py            # generický (list záložek, active index)
    │   ├── chat_message.py
    │   ├── chat_input.py
    │   ├── context_panel.py      # shell + helpery pro pravý panel
    │   ├── language_toggle.py    # přepínač EN / CS
    │   ├── theme_toggle.py       # přepínač dark / light
    │   └── placeholder.py        # výchozí "připravuje se" view
    ├── sections/                 # FEATURE FOLDERS - 1 složka = 1 položka v sidebaru
    │   ├── __init__.py           # auto-discovery, řadí podle (order, key)
    │   ├── _base.py              # Section dataclass
    │   ├── SECTION_TEMPLATE/     # šablona pro novou sekci (READ ME)
    │   ├── dashboard/
    │   ├── ai_career/            # plně postavené (chat se životopisem)
    │   ├── ai_legal/             # placeholder
    │   ├── ai_business/          # placeholder
    │   ├── ai_marketing/         # plně postavené podle návrhu
    │   ├── ai_finance/           # placeholder
    │   ├── ai_study/             # placeholder
    │   └── ai_documents/         # placeholder
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

- Tříslupcový layout odpovídající přiloženému návrhu
- **Přepínač jazyka** EN ↔ CS v sidebaru (default English, jak chtěl tým)
- Přepínání mezi sekcemi v levém sidebaru (auto-discovery)
- Přepínač světlý / tmavý režim
- **AI Životopis / Kariéra** - chat se 4 ukázkovými zprávami, odrážkami, akčními chipy a přílohou
- **AI Marketing** - plně postavený podle dodaného návrhu (vlastní záložky, chat s "Instagram příspěvkem", phone mockup nakreslený přes Flet, brief panel, rychlé akce)
- Pravý panel s dokumenty, rychlými akcemi a historií konverzací

## Co zatím **neumí** (záměrně)

- Žádná skutečná AI ani LLM volání
- Vstup zpráv neukládá nic do stavu
- Tlačítka jsou převážně dekorativní

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
