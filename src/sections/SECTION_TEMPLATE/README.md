# Šablona sekce

Tahle složka je **šablona**, sama se v aplikaci nezobrazuje (auto-discovery
v [src/sections/__init__.py](../__init__.py) ji přeskakuje). Použij ji jako
startovací bod, když přidáváš novou sekci.

## Jak přidat novou sekci

1. **Zkopíruj tuhle složku** na `src/sections/<svuj_klic>/` (např.
   `src/sections/ai_research/`). Klíč musí být `snake_case` a unikátní.
2. **Přejmenuj importy** uvnitř `section.py` a `view.py` z
   `src.sections.SECTION_TEMPLATE.*` na `src.sections.<svuj_klic>.*`.
3. **Uprav `strings.py`** - aspoň `nav_label` a `title` v obou jazycích
   (`en` + `cs`). Další klíče si přidávej, jak budeš stavět view.
4. **Uprav `section.py`**:
   - `key="<svuj_klic>"` (musí odpovídat názvu složky)
   - `icon=ft.Icons.<COKOLI_OUTLINED>`
   - `order=<int>` - viz tabulka níž, vyber volné číslo
   - volitelně přidej `build_context=...` pokud chceš pravý panel
5. **Uprav `view.py`** - vrať `ft.Control`, který tvoří hlavní obsah.
   Inspiruj se v [`ai_cv/view.py`](../ai_cv/view.py) (jednoduchý
   chat) nebo [`ai_marketing/view.py`](../ai_marketing/view.py) (vlastní
   layout s mockupem).
6. **(Volitelné) Pravý panel** - přidej `context.py` s funkcí
   `build_context(theme, lang)` a v `section.py` ji předej do `Section(...,
   build_context=build_context)`. Viz [`ai_cv/context.py`](../ai_cv/context.py).
7. **(Volitelné) Mock data** - přidej `data.py` se svými konstantami.
   Žádný globální mock soubor není potřeba.
8. **Spusť `python main.py`** a koukni, jestli se sekce objevila v levém
   sidebaru a jestli funguje přepínač jazyka.

## Tabulka order hodnot

Drž 10 mezer mezi existujícími sekcemi, ať máš kam vkládat nové bez
nutnosti přečíslovávat:

| order | section             | owner       |
| ----- | ------------------- | ----------- |
| 10    | `dashboard`         | volné       |
| 20    | `ai_cv`         | Fearplay    |
| 25    | `ai_jobs`           | Fearplay    |
| 25    | `ai_linkedin`       | volné       |
| 30    | `ai_legal`          | volné       |
| 40    | `ai_business`       | volné       |
| 50    | `ai_marketing`      | Fearplay    |
| 60    | `ai_finance`        | volné       |
| 70    | `ai_study`          | volné       |
| 80    | `ai_documents`      | volné       |
| 85    | `ai_doc_assistant`  | Fearplay    |
| 100   | (default)           | -           |

Když dva lidi vyberou stejný `order`, řadí se podle `key` abecedně - žádný
merge konflikt na sdíleném seznamu nevznikne.

## Co NESMÍŠ udělat

- Neměň `src/app.py` ani `src/components/sidebar.py` kvůli své sekci. Jsou
  čistě generické a o existenci sekcí se dozví přes auto-discovery.
- Nepřidávej překlady své sekce do `src/i18n.py`. Patří do tvého vlastního
  `strings.py` ve složce sekce.
- Nedávej mock data do sdílených souborů. Patří do `data.py` ve složce
  sekce.
