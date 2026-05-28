"""Temporary offscreen smoke test for Track A changes."""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

app = QApplication([])

from src.app import AIHubApp
from src.theme import get_theme
import src.sections.dashboard.view as dview
import src.sections.dashboard.context as dctx

t = get_theme("dark")
tl = get_theme("light")

# Dashboard view + context, both langs, both themes.
for theme in (t, tl):
    for lang in ("cs", "en"):
        dview.build_view(theme, lang)
        dctx.build_context(theme, lang)
print("dashboard build OK")

# Full app shell + section switching (exercises sidebar update_theme + fade).
w = AIHubApp()
w.build()
for key in ("ai_finance", "ai_career", "ai_linkedin", "ai_bug_report", "ai_jobs", "dashboard"):
    w.set_section(key)
print("app set_section OK")

# Bug report history tab.
import src.sections.ai_bug_report.tab_history as bh
bh.build_history_tab(t, "cs")
bh.build_history_tab(tl, "en")
print("bug report history OK")

print("ALL SMOKE OK")
