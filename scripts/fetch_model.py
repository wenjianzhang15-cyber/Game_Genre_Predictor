"""Retrieve the verified deployment state_dict without loading/executing it."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "085eedcd43b9076a80c1e88e3e2e085a76950aec"
URL = f"https://huggingface.co/spaces/Legend0908/game-genre-demo/resolve/{COMMIT}/best_model.pth"
SHA256 = "5d4b774fa6514e1aba92ede0ad2fba43386141fdbfebfa54b299ef8229e4f3f0"
SIZE = 94387665


def verify(path):
    if path.stat().st_size != SIZE:
        raise ValueError(f"Unexpected model size: {path.stat().st_size}; expected {SIZE}")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != SHA256:
        raise ValueError("Model SHA-256 does not match the verified HF snapshot")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="Use the original_hf model from the local handoff instead of downloading")
    args = parser.parse_args()
    destination = ROOT / "best_model.pth"
    if destination.exists():
        verify(destination)
        print("Existing model verified; no changes needed.")
        return
    fd, name = tempfile.mkstemp(prefix=".model-", suffix=".part", dir=ROOT)
    os.close(fd)
    temporary = Path(name)
    try:
        if args.source:
            verify(args.source)
            shutil.copyfile(args.source, temporary)
        else:
            with urllib.request.urlopen(URL, timeout=60) as response, temporary.open("wb") as output:
                total = 0
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > SIZE:
                        raise ValueError("Download exceeds expected model size")
                    output.write(chunk)
        verify(temporary)
        temporary.replace(destination)
        print(f"Verified model ready: {destination}")
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
