"""Module-level singleton state for the My Profile section.

Holds the in-session uploads + the structured profile while the user is
editing. The authoritative copy lives on disk via
:mod:`src.services.career_profile_store`; this singleton is the working
buffer the view binds to (so theme/lang rebuilds don't lose unsaved
inputs).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class UploadedFile:
    path: str
    name: str
    ext: str
    size_bytes: int
    text: str


@dataclass
class MyProfileState:
    # Inputs.
    resume: Optional[UploadedFile] = None
    linkedin: Optional[UploadedFile] = None
    github_url: str = ""
    github_skip: bool = False
    github_profile: Any = None  # GitHubProfile | None
    notes: str = ""

    # Extracted structured profile (CAREER_PROFILE_SCHEMA shape).
    profile: Optional[dict] = None

    # Runtime flags.
    activity: str = "ready"  # ready | scraping | analyzing | error
    building: bool = False
    last_error: str = ""
    demo_mode: bool = False

    # True once we've hydrated this singleton from disk for this session,
    # so the view doesn't clobber unsaved edits on every rebuild.
    hydrated: bool = False

    def reset_inputs(self) -> None:
        self.resume = None
        self.linkedin = None
        self.github_url = ""
        self.github_skip = False
        self.github_profile = None
        self.notes = ""
        self.last_error = ""
        self.activity = "ready"


STATE = MyProfileState()
