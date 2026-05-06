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
    ├── app.py                    # AIHubApp - stav, layout, routing
    ├── components/               # znovupoužitelné UI prvky
    │   ├── sidebar.py
    │   ├── nav_item.py
    │   ├── user_card.py
    │   ├── section_card.py
    │   ├── document_chip.py
    │   ├── header.py
    │   ├── tab_bar.py
    │   ├── chat_message.py
    │   ├── chat_input.py
    │   └── context_panel.py
    ├── views/                    # jednotlivé obrazovky
    │   ├── chat_view.py          # hlavní view (AI Životopis / Kariéra)
    │   └── placeholder_view.py   # placeholder pro ostatní sekce
    └── data/
        └── mock.py               # mock data (zprávy, dokumenty, historie...)
```

## Co umí

- Tříslupcový layout odpovídající přiloženému návrhu
- Přepínání mezi sekcemi v levém sidebaru
- Přepínač světlý / tmavý režim
- Chat view se 4 ukázkovými zprávami (uživatel + asistent), odrážkami, akčními chipy a přílohou
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
