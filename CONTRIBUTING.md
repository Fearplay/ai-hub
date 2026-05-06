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

## Pravidla pro kód

- Komponenty žijí v `src/components/`, obrazovky v `src/views/`, data v `src/data/`.
- Nové barvy přidávej do [src/theme.py](src/theme.py), nikdy je nehardcoduj v komponentě.
- Mock data (zprávy, položky menu...) patří do [src/data/mock.py](src/data/mock.py).
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
