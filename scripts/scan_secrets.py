"""Download a pinned public Gitleaks release, verify checksums, scan this Git history.

The scanner lives only in a temporary directory. No binary is vendored or installed globally.
"""

import hashlib
import io
from pathlib import Path
import platform
import subprocess
import tarfile
import tempfile
import urllib.request

VERSION = "8.30.1"
BASE = f"https://github.com/gitleaks/gitleaks/releases/download/v{VERSION}/"


def download(name):
    with urllib.request.urlopen(BASE + name, timeout=60) as response:
        data = response.read(40 * 1024 * 1024 + 1)
    if len(data) > 40 * 1024 * 1024:
        raise RuntimeError("Unexpectedly large scanner release.")
    return data


def main():
    system = platform.system().lower()
    machine = platform.machine().lower()
    arch = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "x64", "amd64": "x64"}.get(machine)
    if system not in ("darwin", "linux") or arch is None:
        raise RuntimeError("Scanner helper supports macOS/Linux on arm64/x64.")
    filename = f"gitleaks_{VERSION}_{system}_{arch}.tar.gz"
    checksums = download(f"gitleaks_{VERSION}_checksums.txt").decode()
    expected = next(
        (
            line.split()[0]
            for line in checksums.splitlines()
            if len(line.split()) == 2 and line.split()[1].lstrip("*") == filename
        ),
        None,
    )
    if expected is None:
        raise RuntimeError("Scanner archive is missing from upstream checksums.")
    archive = download(filename)
    if hashlib.sha256(archive).hexdigest() != expected:
        raise RuntimeError("Scanner checksum mismatch.")
    root = Path(__file__).resolve().parents[1]
    subprocess.run(["git", "rev-parse", "--git-dir"], cwd=root, check=True, capture_output=True)
    with tempfile.TemporaryDirectory(prefix="workstation-scanner-") as d:
        binary = Path(d) / "gitleaks"
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
            member = bundle.getmember("gitleaks")
            if not member.isfile() or member.size > 100 * 1024 * 1024:
                raise RuntimeError("Invalid scanner executable member.")
            binary.write_bytes(bundle.extractfile(member).read())
        binary.chmod(0o700)
        # Scan the full new repository history, not installed virtualenvs.
        subprocess.run(
            [str(binary), "git", str(root), "--redact", "--no-banner", "--log-opts=--all"], check=True
        )
    print(f"PASS: Gitleaks {VERSION}; full Git history, redacted output, verified release checksum.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
