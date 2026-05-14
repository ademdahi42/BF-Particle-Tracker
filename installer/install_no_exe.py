from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


APP_NAME = "BF-Particle-Tracker"


def run(command: list[str], cwd: Path) -> None:
    print(">", " ".join(command))
    subprocess.run(command, cwd=str(cwd), check=True)


def desktop_dir() -> Path:
    return Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"


def start_menu_dir() -> Path:
    return Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / APP_NAME


def write_launcher(path: Path, project_root: Path) -> None:
    launcher = project_root / "run_app.bat"
    text = f'@echo off\r\ncd /d "{project_root}"\r\n"{launcher}"\r\n'
    path.write_text(text, encoding="utf-8")


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    requirements = project_root / "requirements.txt"
    venv_dir = project_root / ".venv_app"
    python_exe = venv_dir / "Scripts" / "python.exe"

    print(f"Installing {APP_NAME} without an executable installer")
    print(f"Project folder: {project_root}")
    print("")

    if sys.version_info < (3, 10):
        print("ERROR: Python 3.10 or newer is required.")
        return 1

    if not requirements.exists():
        print(f"ERROR: missing requirements file: {requirements}")
        return 1

    try:
        if not python_exe.exists():
            print("Creating local Python environment...")
            run([sys.executable, "-m", "venv", str(venv_dir)], project_root)
        else:
            print("Local Python environment already exists.")

        print("Installing Python packages...")
        run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], project_root)
        run([str(python_exe), "-m", "pip", "install", "-r", str(requirements)], project_root)

        print("Checking application files...")
        run([str(python_exe), "-m", "py_compile", "main.py", "gui.py", "processing.py"], project_root)

        print("Creating launch shortcuts...")
        desktop = desktop_dir()
        if desktop.exists():
            write_launcher(desktop / f"{APP_NAME}.cmd", project_root)

        menu_dir = start_menu_dir()
        menu_dir.mkdir(parents=True, exist_ok=True)
        write_launcher(menu_dir / f"{APP_NAME}.cmd", project_root)

    except subprocess.CalledProcessError as exc:
        print("")
        print(f"Installation failed with exit code {exc.returncode}.")
        return int(exc.returncode)
    except Exception as exc:
        print("")
        print(f"Installation failed: {exc}")
        return 1

    print("")
    print("Installation completed.")
    print("Launch the app with run_app.bat or the BF-Particle-Tracker shortcut.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
