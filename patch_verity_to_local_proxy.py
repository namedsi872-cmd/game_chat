from __future__ import annotations

import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path


JAR_PATH = Path(r"C:\Users\Zephy\AppData\Roaming\.minecraft\versions\1.21.1-NeoForge_21.1.248\mods\verity-3.4.1.jar")
BACKUP_DIR = Path(__file__).resolve().parent / "patch_backups"

REPLACEMENTS = {
    b"https://api.groq.com/openai/v1/chat/completions": b"http://127.0.0.1:800/openai/v1/chat/completions",
    b"https://api.groq.com/openai/v1/audio/speech": b"http://127.0.0.1:800/openai/v1/audio/speech",
    b"https://api.groq.com/openai/v1/audio/transcriptions": b"http://127.0.0.1:800/openai/v1/audio/transcriptions",
}


def validate_lengths() -> None:
    for old, new in REPLACEMENTS.items():
        if len(old) != len(new):
            raise ValueError(f"replacement length mismatch: {old!r} -> {new!r}")


def backup_original() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / JAR_PATH.name
    shutil.copy2(JAR_PATH, backup_path)
    return backup_path


def patch_jar() -> None:
    if not JAR_PATH.exists():
        raise FileNotFoundError(f"jar not found: {JAR_PATH}")

    validate_lengths()
    backup_path = backup_original()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        patched_jar = tmpdir_path / JAR_PATH.name

        with zipfile.ZipFile(JAR_PATH, "r") as src, zipfile.ZipFile(
            patched_jar,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as dst:
            for info in src.infolist():
                data = src.read(info.filename)
                if info.filename == "varmite/verity/entity/AI/AiAPI.class":
                    for old, new in REPLACEMENTS.items():
                        if old not in data:
                            raise RuntimeError(f"expected string missing in {info.filename}: {old!r}")
                        data = data.replace(old, new)
                dst.writestr(info, data)

        shutil.copy2(patched_jar, JAR_PATH)

    print(f"Patched: {JAR_PATH}")
    print(f"Backup : {backup_path}")


if __name__ == "__main__":
    patch_jar()
