from dataclasses import replace

import pytest

from h3ir.clips import ClipRequest, compile_clips
from h3ir.models import Brief, DialogueLine, Mode


class DraftBackend:
    class cfg:
        model = "offline-test"

    def require_available(self):
        pass

    def server_version(self):
        return "offline-test"


def test_real_compiler_preserves_clip_boundaries_dialogue_and_grid():
    first = Brief(intent="A courier arrives at a lighthouse.", seconds=5,
                  shots=1, mode=Mode.T2VA, canvas=(864, 480),
                  dialogue=[DialogueLine("I'm here, Captain!")])
    second = replace(first, intent="The courier lights a lamp.", seconds=8, dialogue=[])
    progress = []
    result = compile_clips([ClipRequest("arrival", first), ClipRequest("lamp", second)],
                           shared_context="Yellow raincoat.", backend=DraftBackend(), llm=False,
                           on_progress=lambda *args: progress.append(args))
    a, b = [clip.to_dict() for clip in result]
    assert a["id"] == "arrival" and b["id"] == "lamp"
    assert (a["frames"], b["frames"]) == (124, 192)
    assert a["seconds"] == 124 / 24
    assert "I'm here, Captain!" in a["prompt"]
    assert "I'm here, Captain!" not in b["prompt"]
    assert a["canvas"] == [864, 480]
    assert "Yellow raincoat." in result[0].document.provenance["request"]
    assert first.intent == "A courier arrives at a lighthouse."
    assert a["source"] == "draft" and a["fallback_reason"]
    assert progress == [(1, 2, "arrival"), (2, 2, "lamp")]


@pytest.mark.parametrize("requests", [[],
    [ClipRequest("x", Brief(intent="a fox")), ClipRequest("x", Brief(intent="a dog"))],
    [ClipRequest("", Brief(intent="a fox"))],
    [ClipRequest("x", Brief(intent="a fox", seconds=float("nan")))],
    [ClipRequest("x", Brief(intent="a fox")), ClipRequest("y", Brief(intent=""))],
])
def test_bad_batch_is_refused_before_any_model_call(requests, monkeypatch):
    def unexpected(*a, **kw):
        pytest.fail("compiled a partially invalid batch")
    monkeypatch.setattr("h3ir.clips.compile_brief", unexpected)
    with pytest.raises(ValueError):
        compile_clips(requests)
