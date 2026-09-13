"""Normalize source archive metadata and generate release checksums.

Build first. Archive ownership must not reveal the build machine's username/group.
"""

import copy
import gzip
import hashlib
from pathlib import Path
import subprocess
import tarfile
import tempfile


def normalize_sdist(path: Path, epoch: int) -> None:
    with tempfile.TemporaryDirectory(prefix="release-normalize-", dir=path.parent) as directory:
        destination = Path(directory) / path.name
        with tarfile.open(path, "r:gz") as source, destination.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=epoch) as compressed:
                with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as target:
                    for original in source.getmembers():
                        name = Path(original.name)
                        if (
                            name.is_absolute()
                            or ".." in name.parts
                            or not (original.isfile() or original.isdir())
                        ):
                            raise ValueError(
                                "Release archive must contain only relative regular files/directories."
                            )
                        member = copy.copy(original)
                        member.uid = member.gid = 0
                        member.uname = member.gname = ""
                        member.mtime = epoch
                        member.pax_headers = {
                            key: value for key, value in member.pax_headers.items() if key in ("path", "size")
                        }
                        content = source.extractfile(original) if original.isfile() else None
                        try:
                            target.addfile(member, content)
                        finally:
                            if content is not None:
                                content.close()
        destination.replace(path)


def main():
    from agent_workstation import __version__

    root = Path(__file__).resolve().parents[1]
    epoch = int(subprocess.check_output(["git", "log", "-1", "--format=%ct"], cwd=root, text=True).strip())
    dist = root / "dist"
    archive = dist / f"agent_workstation-{__version__}.tar.gz"
    wheel = dist / f"agent_workstation-{__version__}-py3-none-any.whl"
    if not archive.is_file() or not wheel.is_file():
        raise RuntimeError("Build the wheel and sdist before preparing a release.")
    normalize_sdist(archive, epoch)
    lines = [f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}" for path in (archive, wheel)]
    (dist / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("PASS: normalized archive ownership/timestamps; SHA256SUMS generated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
