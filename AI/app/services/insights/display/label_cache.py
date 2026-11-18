"""A workbook's label readings kept on disk, so a reading asked once is never asked again.

Without it every restart asks the model again, and a failed call (an exhausted quota, no
network) shows the workbook's English labels although they were read before. The file is
keyed like the in-process cache; anything unreadable is ignored, and a write failure only
means the next process asks again.
"""
import json
import os
import tempfile
from pathlib import Path


def _path(key):
    root = os.getenv("LABEL_READINGS_DIR") or str(Path(tempfile.gettempdir()) / "excel-ai-agent-label-readings")
    return Path(root) / f"{key}.json"


def load_readings(key):
    """{label casefold: [korean, counter]} saved for the workbook, or {}."""
    try:
        data = json.loads(_path(key).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {label: read for label, read in data.items() if isinstance(label, str) and isinstance(read, list)
            and len(read) == 2 and all(isinstance(part, str) for part in read)} if isinstance(data, dict) else {}


def save_readings(key, readings):
    try:
        path = _path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(readings, ensure_ascii=False), encoding="utf-8")
        temporary.replace(path)
    except OSError:
        pass
