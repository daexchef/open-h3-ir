"""Compile caller-owned clip lists without a renderer or ComfyUI dependency.

The caller owns clip boundaries. The existing compiler owns each clip's H3
structure, validation, dialogue substitution and frame grid.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Callable, Sequence

from .compile import compile_brief, check_request
from .models import Brief, IRDocument


@dataclass(frozen=True)
class ClipRequest:
    id: str
    brief: Brief


@dataclass(frozen=True)
class CompiledClip:
    id: str
    document: IRDocument

    def to_dict(self) -> dict:
        doc = self.document
        target = doc.plan.target
        return {
            "id": self.id, "mode": doc.mode.value, "prompt": doc.prompt,
            "requested_seconds": target.nominal_seconds,
            "frames": target.frames, "fps": target.fps,
            "seconds": target.effective_seconds, "canvas": list(target.canvas),
            "source": doc.source, "fallback_reason": doc.fallback_reason,
            "findings": [str(f) for f in doc.findings],
        }


def compile_clips(clips: Sequence[ClipRequest], *, shared_context: str = "",
                  backend=None, seed: int = 7,
                  on_progress: Callable[[int, int, str], None] | None = None,
                  **compile_options) -> tuple[CompiledClip, ...]:
    """Compile in order, returning no partial batch on failure.

    Assets remain per-brief; no implicit reference sharing or renumbering occurs.
    Shared context is lower-priority prose, never an extra structural prompt.
    An unchanged seed is intentional: reordering clips must not change a take.
    """
    clips = tuple(clips)
    if not clips:
        raise ValueError("Provide at least one clip.")
    seen = set()
    prepared = []
    # Validate the whole list before spending a model call.
    for clip in clips:
        if not isinstance(clip.id, str) or not clip.id.strip() or clip.id in seen:
            raise ValueError("Clip IDs must be non-empty and unique.")
        seen.add(clip.id)
        if not math.isfinite(clip.brief.seconds):
            raise ValueError(f"Clip {clip.id}: seconds must be finite.")
        check_request(clip.brief)
        intent = clip.brief.intent
        if shared_context.strip():
            intent += ("\n\nShared continuity context (apply only where the clip request "
                       "above leaves a choice open):\n" + shared_context.strip())
        prepared.append(replace(clip.brief, intent=intent))
    results = []
    for index, (clip, brief) in enumerate(zip(clips, prepared), 1):
        doc = compile_brief(brief, backend=backend, seed=seed, **compile_options)
        if not doc.ok:
            raise ValueError(f"Clip {clip.id} failed validation: {doc.errors}")
        results.append(CompiledClip(clip.id, doc))
        if on_progress:
            on_progress(index, len(clips), clip.id)
    return tuple(results)
