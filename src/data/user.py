"""Globally shared mock data (only the logged-in user belongs here).

Per-section mock data lives next to its section, in
``src/sections/<key>/data.py``.
"""

from __future__ import annotations


USER: dict[str, str] = {
    "first_name": "Jan",
    "last_name": "Novák",
    # ``name`` is kept as the composed full name for any caller that
    # still reads a single field; the sidebar profile card prefers the
    # ``first_name`` / ``last_name`` pair so it can show them split.
    "name": "Jan Novák",
    "email": "jan.novak@email.com",
    # Subscription tier shown under the name in the sidebar profile card.
    "plan": "pro",
}
