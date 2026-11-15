"""Import pinned public datasets without combining their databases or licenses."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

REVISION = "c4a0be3250d9bb7c1df34f3e8c42c8652f9404b9"
FILES = ("audio-signals.json", "voice-guides.json", "subway-stations.json", "crosswalks.json", "osm-walk-nodes.json")
ROOT = Path(__file__).resolve().parents[1] / "app" / "data" / "accessibility"

def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    manifest = {"repository": "https://github.com/Engccer/gildongmu", "revision": REVISION, "files": {}}
    for name in FILES:
        url = f"https://raw.githubusercontent.com/Engccer/gildongmu/{REVISION}/src/lib/data/{name}"
        with urlopen(Request(url, headers={"User-Agent": "Galjido-dataset-import"}), timeout=60) as response:
            content = response.read()
        json.loads(content)
        (ROOT / name).write_bytes(content)
        manifest["files"][name] = {"url": url, "sha256": hashlib.sha256(content).hexdigest()}
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
