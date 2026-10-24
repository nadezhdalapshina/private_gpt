#!/usr/bin/env python3
"""Version local image URLs based on actual file contents (SHA-256).

Run after an image is replaced with the same filename. Only changes <img src>
references to existing local files; leaves external images untouched.
"""
import hashlib
import re
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
IMAGE_SRC = re.compile(r'(?P<prefix><img\b[^>]*?\bsrc=")(?P<url>images/[^"]+)(?P<suffix>")', re.I | re.S)

def update(match):
    src = match.group("url")
    filename = urlsplit(src.replace("&amp;", "&")).path
    if not filename.startswith("images/"):
        return match.group(0)
    path = ROOT / filename
    if not path.is_file():
        return match.group(0)
    version = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    new_url = filename + "?v=" + version
    return match.group("prefix") + new_url + match.group("suffix")

def main():
    original = INDEX.read_text(encoding="utf-8")
    updated = IMAGE_SRC.sub(update, original)
    if updated != original:
        INDEX.write_text(updated, encoding="utf-8")
        print("Updated image URL versions in index.html")
    else:
        print("Image URL versions are already up to date")

if __name__ == "__main__":
    main()
