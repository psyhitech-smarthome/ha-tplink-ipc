"""Reject accidental runtime artifacts and credential-like values in a release."""

from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
for path in root.rglob("*"):
    if not path.is_file() or any(
        part in {".git", "__pycache__", ".venv", ".ruff_cache"} for part in path.parts
    ):
        continue
    if path.resolve() == Path(__file__).resolve():
        continue  # This file contains the detection expressions themselves.
    assert path.suffix not in {
        ".db",
        ".sqlite",
        ".pem",
        ".key",
        ".jpg",
        ".png",
        ".mp4",
    }, path
    text = path.read_text()
    for pattern in [
        r"rtsp://[^\s/]+:[^\s/]+@",
        r"gh[pousr]_[A-Za-z0-9]{30,}",
        r"eyJ[A-Za-z0-9_-]{15,}\.eyJ[A-Za-z0-9_-]+\.",
        r"-----BEGIN .*PRIVATE KEY-----",
    ]:
        assert not re.search(pattern, text), (
            f"Possible secret: {path.relative_to(root)}"
        )
print("Public tree check passed")
