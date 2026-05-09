"""Shared service-layer modules.

Sections never import vendor SDKs (``openai`` / ``anthropic``) or filesystem
helpers directly - they go through this package. That keeps every section's
files focused on copy + UI + prompts, and lets us swap providers or
storage backends without touching every section.

Modules:

* :mod:`src.services.secrets` - OS-native key storage via ``keyring``.
* :mod:`src.services.ai_provider` - one entry point for OpenAI + Anthropic.
* :mod:`src.services.cost_tracker` - per-session token / dollar accounting.
* :mod:`src.services.job_scraper` - URL → cleaned job posting text.
* :mod:`src.services.file_parser` - PDF / DOCX / TXT / HTML → plain text.
* :mod:`src.services.github_client` - public profile + repo summary.
* :mod:`src.services.exporter` - Markdown → HTML / DOCX / PDF writers.
* :mod:`src.services.store` - JSON-backed history & run output paths.
* :mod:`src.services.settings_store` - chosen provider / model + flags.
* :mod:`src.services.clipboard` - synchronous OS clipboard (replaces the
  flaky ``ft.Clipboard`` async service).
"""
