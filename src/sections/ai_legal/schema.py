"""JSON schemas for the AI Legal section.

The chat and quick-action calls return plain markdown prose, so there
is no structured-output schema for them - we pass ``schema=None`` into
:func:`src.services.ai_provider.run` which keeps the model in free-text
mode. The constant below exists so call-sites read consistently next to
other AI sections that *do* use structured outputs.
"""

from __future__ import annotations

from typing import Optional


CHAT_SCHEMA: Optional[dict] = None
QUICK_ACTION_SCHEMA: Optional[dict] = None
