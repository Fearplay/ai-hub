@echo off
REM ============================================================
REM AI Hub - one-click Windows build script (PySide6 + PyInstaller)
REM ============================================================
REM Builds a single-file dist\AIHub.exe with no prerequisites.
REM
REM What this does (in order):
REM   1. Find a working Python 3.10+:
REM      - try "python" on PATH (the usual case)
REM      - fall back to "py -3" (the Windows Python Launcher; ships with
REM        every python.org install and stays on PATH even when the user
REM        unchecked "Add python.exe to PATH" during install)
REM      - if neither works, install via winget; if winget is missing,
REM        print a python.org link and exit
REM   2. Create / activate a project-local .venv\
REM   3. Upgrade pip and install requirements.txt + pyinstaller
REM   4. Run "pyinstaller" to bundle main.py into one .exe (with the
REM      Material Symbols Rounded icon font baked into
REM      ``assets\fonts\`` so glyphs render on a clean machine)
REM   5. Print the output path
REM
REM Skips the rebuild when dist\AIHub.exe is newer than every .py
REM under main.py and src\.  Force a full rebuild with:  build_exe.bat --force
REM ============================================================

setlocal enabledelayedexpansion
pushd "%~dp0"

set "FORCE_REBUILD=0"
if /I "%~1"=="--force" set "FORCE_REBUILD=1"
if /I "%~1"=="-f" set "FORCE_REBUILD=1"

set "EXIT_CODE=0"
set "PYCMD="

echo.
echo ============================================================
echo  AI Hub - Windows build (PySide6)
echo ============================================================

REM ---------- 1. Python ----------
REM Try "python" first (most common), then "py -3" (Windows Python Launcher).
REM We don't enforce a minimum version with a regex here - if the chosen
REM interpreter is too old, "pip install -r requirements.txt" will fail
REM later with a clear error.
where python >nul 2>nul
if not errorlevel 1 set "PYCMD=python"

if not defined PYCMD (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 --version >nul 2>nul
        if not errorlevel 1 set "PYCMD=py -3"
    )
)

if not defined PYCMD (
    echo [1/5] Python not found on PATH. Trying winget install...
    where winget >nul 2>nul
    if errorlevel 1 (
        echo  ^> winget is not available either.
        echo  ^> Please install Python 3.10+ manually:
        echo     https://www.python.org/downloads/windows/
        echo     ^(check "Add python.exe to PATH" during install^)
        set "EXIT_CODE=1"
        goto :done
    )
    winget install -e --id Python.Python.3.13 --accept-source-agreements --accept-package-agreements
    if errorlevel 1 (
        echo  ^> winget install failed. Install Python 3.10+ manually:
        echo     https://www.python.org/downloads/windows/
        set "EXIT_CODE=1"
        goto :done
    )
    REM Refresh PATH for this session so the freshly installed Python is visible.
    for /f "usebackq tokens=2,*" %%A in (`reg query "HKCU\Environment" /v PATH 2^>nul`) do set "PATH=%%B;%PATH%"
    where python >nul 2>nul
    if not errorlevel 1 set "PYCMD=python"
    if not defined PYCMD (
        where py >nul 2>nul
        if not errorlevel 1 (
            py -3 --version >nul 2>nul
            if not errorlevel 1 set "PYCMD=py -3"
        )
    )
)

if not defined PYCMD (
    echo  ^> Python installed but not yet on PATH. Open a new terminal and re-run.
    set "EXIT_CODE=1"
    goto :done
)

echo [1/5] Python OK ^(using "!PYCMD!"^).
!PYCMD! --version

REM ---------- 2. venv ----------
if not exist ".venv\Scripts\activate.bat" (
    echo [2/5] Creating .venv ...
    !PYCMD! -m venv .venv
    if errorlevel 1 (
        echo  ^> Failed to create .venv. Check Python install.
        set "EXIT_CODE=1"
        goto :done
    )
) else (
    echo [2/5] .venv already exists.
)
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
    echo  ^> Failed to activate .venv.
    set "EXIT_CODE=1"
    goto :done
)

REM From this point on, "python", "pip" and "pyinstaller" resolve to the
REM venv binaries because activate.bat prepended .venv\Scripts to PATH.

REM ---------- 3. dependencies ----------
echo [3/5] Installing dependencies ...
python -m pip install --upgrade pip --quiet --disable-pip-version-check
if errorlevel 1 goto :pip_failed
python -m pip install -r requirements.txt --quiet --disable-pip-version-check
if errorlevel 1 goto :pip_failed
python -m pip install pyinstaller --quiet --disable-pip-version-check
if errorlevel 1 goto :pip_failed
goto :pip_done
:pip_failed
echo  ^> pip install failed.
set "EXIT_CODE=1"
goto :done
:pip_done

REM ---------- 4. up-to-date check ----------
if "%FORCE_REBUILD%"=="1" goto :do_build
if not exist "dist\AIHub.exe" goto :do_build

REM Build only if any .py is newer than dist\AIHub.exe
for /f %%F in ('dir /b /s /a:-d main.py src\*.py 2^>nul') do (
    xcopy /D /Y /L "%%F" "dist\AIHub.exe" 2>nul | find " 1 File(s)" >nul && goto :do_build
)
echo [4/5] dist\AIHub.exe is up to date. Skipping rebuild.
echo       ^(use "build_exe.bat --force" to rebuild anyway^)
goto :done

:do_build
echo [4/5] Bundling with PyInstaller ...
if exist "build\" rmdir /S /Q "build" >nul 2>nul
if exist "dist\AIHub.exe" del /Q "dist\AIHub.exe" >nul 2>nul
if exist "AIHub.spec" del /Q "AIHub.spec" >nul 2>nul

set "ICON_ARG="
if exist "assets\icon.ico" set "ICON_ARG=--icon assets\icon.ico"

REM PyInstaller flags:
REM   --onefile --windowed                 -> single-file GUI app, no console
REM   --name AIHub                         -> output name
REM   --add-data "src;dst"                 -> bundle the Material Symbols
REM                                            Rounded font subset (.otf)
REM                                            and the codepoints map
REM                                            (Windows uses ; as separator)
REM   --hidden-import pyperclip             -> defensive; pyperclip is sometimes
REM                                            picked up via lazy try/except
REM   --collect-submodules PySide6         -> bring all of PySide6's dynamic
REM                                            submodules into the bundle so
REM                                            QSyntaxHighlighter, QtSvg etc.
REM                                            don't fail at runtime.
REM   --collect-submodules truststore      -> truststore loads its OS-specific
REM                                            backend (_windows / _macos /
REM                                            _openssl) at import time; force
REM                                            PyInstaller to bundle all three
REM                                            so the .exe trusts the system
REM                                            CA store on a clean machine.
REM   --collect-submodules yfinance        -> yfinance lazily imports a handful
REM                                            of internal modules (multi.py,
REM                                            scrapers, utils). Force the bundle
REM                                            so the AI Finance live tickers
REM                                            still resolve in the frozen .exe.
REM   --collect-submodules src.sections    -> sections are auto-discovered at
REM                                            runtime via pkgutil.iter_modules
REM                                            (see src\sections\__init__.py).
REM                                            PyInstaller's static analyser
REM                                            cannot see the dynamic
REM                                            ``importlib.import_module(...)``
REM                                            calls, so without this flag the
REM                                            frozen .exe sees ZERO sections
REM                                            and crashes at startup with
REM                                            ``[WinError 3] ... \src\sections``.
REM   --collect-submodules src.services    -> defensive; some services (e.g.
REM                                            html_pdf, ai_provider) lazy-
REM                                            import their backends only when
REM                                            actually called.
pyinstaller --noconfirm --onefile --windowed --name AIHub ^
    --add-data "assets\fonts;assets\fonts" ^
    --hidden-import pyperclip ^
    --collect-submodules PySide6 ^
    --collect-submodules truststore ^
    --collect-submodules yfinance ^
    --collect-submodules src.sections ^
    --collect-submodules src.services ^
    %ICON_ARG% ^
    main.py
if errorlevel 1 (
    echo  ^> pyinstaller failed.
    set "EXIT_CODE=1"
    goto :done
)

if not exist "dist\AIHub.exe" (
    echo  ^> Build finished but dist\AIHub.exe is missing. Check the log above.
    set "EXIT_CODE=1"
    goto :done
)

echo [5/5] Build OK.
echo       Output: %CD%\dist\AIHub.exe

:done
popd
endlocal & exit /b %EXIT_CODE%
