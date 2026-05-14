"""Direction-specific prompt registry.

Each direction module exports a `SPEC: DirectionSpec`. The registry resolves a
direction key to its spec, falling back to a generic spec when no specialised
prompt exists yet. This lets us deepen quality on flagship directions
incrementally without breaking the long tail.
"""
from __future__ import annotations

from .base import (
    CritiqueAxis,
    DirectionSpec,
    DEFAULT_SPEC,
    resolve_spec,
)

__all__ = ["CritiqueAxis", "DirectionSpec", "DEFAULT_SPEC", "resolve_spec"]
