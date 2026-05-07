# Přispívání do AI Hub

Díky, že do toho jdeš s námi. Tohle je pár pravidel, ať si nepřekrýváme práci a ať se v repu udrží pořádek.

## Workflow

1. **Domluva před prací**
   Než se pustíš do větší změny, otevři issue nebo to napiš tomu druhému. Drobné fixy a opravy překlepů můžeš dělat rovnou.

2. **Vlastní branch**
   Vždycky pracuj na vlastní větvi z aktuální `main`. Pojmenování:
   - `feat/<krátký-popis>` - nová funkce, např. `feat/light-mode-polish`
   - `fix/<krátký-popis>` - oprava bugu, např. `fix/sidebar-overflow`
   - `chore/<krátký-popis>` - drobnosti, refaktor, dokumentace
   - `docs/<krátký-popis>` - jen dokumentace

3. **Commity**
   Krátká věta, prefix odpovídá typu:
   - `feat: pridat formularovy rezim`
   - `fix: opravit zalamovani v sidebaru`
   - `chore: aktualizovat README`
   - `docs: doplnit popis komponent`

4. **Pull Request**
   Otevři PR proti `main`. V popisu uveď:
   - co se mění a proč,
   - jak to otestovat (`python main.py` + na co se kouknout),
   - screenshot, pokud měníš UI.

5. **Review**
   Druhý člověk PR projde, schválí (nebo navrhne úpravy) a pak se mergne. Mergujeme jako "Squash and merge", ať je historie čistá.

## Architektura - sekce

Každá položka v levém sidebaru je samostatná **sekce** se svojí složkou v
`src/sections/<klic>/`. Auto-discovery v
[src/sections/__init__.py](src/sections/__init__.py) najde všechny složky a
seřadí je podle `order`.

**Důsledek:** přidání nové sekce nikdy neotvírá `src/app.py`, `src/components/sidebar.py`
ani žádný sdílený mock soubor - jen vytvoříš složku. Žádné merge konflikty.

### Přidání nové sekce

1. Zkopíruj `src/sections/SECTION_TEMPLATE/` na `src/sections/<svuj_klic>/`.
2. Postupuj podle [src/sections/SECTION_TEMPLATE/README.md](src/sections/SECTION_TEMPLATE/README.md).
3. Vyber volný `order` (viz tabulka v README šablony).
4. Spusť `python main.py` a zkontroluj, že sekce sedí v sidebaru a funguje
   přepínač jazyka.

### Vlastnictví sekcí

Aby se nepřekrývala práce, drž se vlastnictví:

| sekce            | owner       |
| ---------------- | ----------- |
| `dashboard`      | volné       |
| `ai_career`      | Fearplay    |
| `ai_legal`       | volné       |
| `ai_business`    | volné       |
| `ai_marketing`   | Fearplay    |
| `ai_finance`     | volné       |
| `ai_study`       | volné       |
| `ai_documents`   | volné       |

Pokud chceš převzít volnou sekci, přepiš tabulku v PR.

## Pravidla pro kód

- **Sekce** žijí v `src/sections/<klic>/`. Mock data sekce patří do `data.py`
  ve složce sekce, překlady do `strings.py`, view do `view.py`,
  registrace do `section.py`.
- **Sdílené komponenty** žijí v `src/components/`. Patří sem jen věci, které
  použije víc než jedna sekce. Pokud potřebuješ něco specifického jen pro
  svoji sekci, dej to do své složky.
- **Globální překlady** (sidebar, "Nová konverzace", "Odeslat", ...) jsou v
  [src/i18n.py](src/i18n.py). **Překlady jednotlivých sekcí** patří do
  `strings.py` té sekce. Tím se překlady jedné sekce neperou s druhou.
- **Globální mock data** (jediná taková je `USER`) jsou v
  [src/data/user.py](src/data/user.py). Nic dalšího sem nepřidávej.
- Nové barvy přidávej do [src/theme.py](src/theme.py), nikdy je nehardcoduj
  v komponentě. (Drobné výjimky pro vizualizace - viz
  `src/sections/ai_marketing/phone_mockup.py`.)
- Před commitnutím spusť aplikaci a koukni, že nic není rozbité (`python main.py`).
- Jednotný styl - 4 mezery na odsazení, žádné tabulátory, snake_case pro funkce a proměnné, PascalCase pro třídy.
- Nepiš redundantní komentáře typu "tady definuji proměnnou". Komentář má smysl jen tam, kde vysvětluje proč, ne co.

## Hlášení chyb

Otevři issue a uveď:

- co jsi dělal,
- co se mělo stát,
- co se ve skutečnosti stalo,
- verzi Pythonu a Fletu (`python --version`, `pip show flet`),
- ideálně screenshot.

## Vývojové prostředí

```bash
python -m venv .venv
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
python main.py
```
