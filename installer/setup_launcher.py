from __future__ import annotations

import subprocess
import sys
from pathlib import Path


APP_NAME = "BF-Particle-Tracker"


def installer_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def main() -> int:
    root = installer_dir().parent
    install_script = installer_dir() / "install.ps1"

    print(f"{APP_NAME} Setup")
    print("=" * (len(APP_NAME) + 6))
    print(f"Project folder: {root}")
    print("")

    if not install_script.exists():
        print(f"ERROR: missing installer script:\n{install_script}")
        input("Press Enter to close...")
        return 1

    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(install_script),
    ]

    try:
        completed = subprocess.run(command, cwd=str(root), check=False)
    except Exception as exc:
        print("")
        print(f"Installation failed: {exc}")
        input("Press Enter to close...")
        return 1

    print("")
    if completed.returncode == 0:
        print("Installation completed successfully.")
    else:
        print(f"Installation failed with exit code {completed.returncode}.")

    input("Press Enter to close...")
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
