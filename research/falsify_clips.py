"""Prove the new clip guards reject planted defects, restoring source afterward.

Run in a clean checkout with the development dependencies installed.
"""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
source = root / "h3ir/clips.py"
original = source.read_bytes()
text = original.decode("utf-8")
cases = [
    ("frame drift", '"frames": target.frames,', '"frames": target.frames + 17,',
     "tests/test_clips.py::test_real_compiler_preserves_clip_boundaries_dialogue_and_grid", 1),
    ("preflight omitted", "    clips = tuple(clips)", "    return ()  # planted preflight omission\n    clips = tuple(clips)",
     "tests/test_clips.py::test_bad_batch_is_refused_before_any_model_call", 5),
]
failed = False
try:
    for name, before, after, test, count in cases:
        if text.count(before) != 1:
            raise RuntimeError(f"BROKEN {name}: mutation anchor moved")
        mutated = text.replace(before, after)
        compile(mutated, str(source), "exec")
        source.write_text(mutated, encoding="utf-8")
        if source.read_text(encoding="utf-8") != mutated:
            raise RuntimeError(f"BROKEN {name}: mutation did not land")
        run = subprocess.run([sys.executable, "-B", "-m", "pytest", test, "-q"],
                             cwd=root, capture_output=True, text=True)
        red = run.returncode == 1 and f"{count} failed" in run.stdout
        print(f"{'RED' if red else 'BROKEN/GREEN'}: {name}")
        if not red:
            print(run.stdout, run.stderr)
            failed = True
        source.write_bytes(original)
finally:
    source.write_bytes(original)
sys.exit(1 if failed else 0)
