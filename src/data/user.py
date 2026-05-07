"""Globally shared mock data (only the logged-in user belongs here).

Per-section mock data lives next to its section, in
``src/sections/<key>/data.py``.
"""

from __future__ import annotations


USER: dict[str, str] = {
    "name": "Jan Novák",
    "email": "jan.novak@email.com",
}
