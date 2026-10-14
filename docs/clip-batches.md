# Individual clip briefs for timeline directors

This fork adds `h3ir.clips.compile_clips`: a renderer-independent way to compile
a caller's ordered clip list with the existing OpenH3-IR pipeline. It does not
load H3 weights, encode conditioning, start ComfyUI, or generate video.

```python
from h3ir.backend import Backend
from h3ir.clips import ClipRequest, compile_clips
from h3ir.models import Brief, DialogueLine, Mode

backend = Backend()  # H3IR_LLM_URL / H3IR_LLM_MODEL / H3IR_LLM_KEY
try:
    clips = compile_clips([
        ClipRequest("arrival", Brief(
            intent="A courier arrives at the lighthouse.", seconds=5,
            canvas=(864, 480), shots=1, mode=Mode.T2VA,
            dialogue=[DialogueLine("I'm here, Captain!")],
        )),
        ClipRequest("lamp", Brief(
            intent="The courier climbs the stairs and lights the lamp.", seconds=8,
            canvas=(864, 480), shots=1, mode=Mode.T2VA,
        )),
    ], backend=backend, seed=7,
       shared_context="Same courier: yellow raincoat, brown satchel. Coastal dusk.")
finally:
    backend.close()

manifest = [clip.to_dict() for clip in clips]
```

Each manifest entry carries the actual prompt, compiler frame count, effective
duration, canvas, source, draft-fallback reason and validation findings. Consume
the frame count rather than rounding the requested seconds again. Five seconds
becomes 124 frames / 5.167 seconds at 24 FPS; eight seconds becomes 192 frames.

Clip IDs must be unique. The whole list is preflighted before compilation; a
failure returns no partial batch. Execution is sequential to avoid overloading a
local LLM. An unchanged seed is passed to each compile, so reordering the list
does not itself change the seed. The caller owns and closes a supplied backend.

The API accepts ordinary `Brief` objects, including their existing asset and
dialogue contracts. References are per-brief; there is no implicit media sharing,
cross-clip relabeling or automatic story generation. Shared context is prose that
fills choices left open by each clip. It does not guarantee character identity.

The accompanying [Motion Director fork](https://github.com/daexchef/ComfyUI-MiniMax-H3-Motion-Director/tree/feat/openh3-clip-prompter)
adds a ComfyUI Clip Prompter node and a T2V timeline adapter. This compiler remains
Apache-2.0; Director retains its upstream GPL-3.0 license and notices. Neither
project's compiler or renderer is copied into the other.

For LM Studio set `H3IR_LLM_URL=http://127.0.0.1:1234/v1` and explicitly name the
model reported by its API. `qwen/qwen3.5-9b` is the initial practical local target;
the upstream project's documented tested model is Qwen3.6-27B. This is not a
comparative model-quality benchmark.
