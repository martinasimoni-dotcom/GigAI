from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import webbrowser
from pathlib import Path
from threading import Timer


LAUNCHER_VERSION = "2026.03.18.5"
LATEST_UPDATES = [
    "Revit mic capture reliability improved (auto-start on open, better timeout tuning, less noisy interim text)",
    "start-api now auto-falls back to next free port (8011+) if requested port is blocked",
    "Default local API port moved to 8010 to avoid persistent 8000 bind conflict",
    "start-api.ps1 now uses robust bind checks and safer stop/recheck flow",
    "Voice pipeline now supports Rafik Claude LLM mapping with safe fallback to local matcher",
    "Fireflies transcript source remains available through /voice/command fallback",
    "Revit Voice Command window UI improved (larger controls, better spacing, DPI-friendly layout)",
]

FRONTEND_URL = "http://localhost:3000"
DASHBOARD_API_URL = "http://localhost:8010"
ORCHESTRATOR_API_URL = "http://localhost:8011"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GigAI main launcher")
    parser.add_argument(
        "--mode",
        choices=("all", "backend", "frontend"),
        default="all",
        help="What to run (default: all)",
    )
    parser.add_argument("--backend-port", type=int, default=8010, help="Backend port")
    parser.add_argument("--orchestrator-port", type=int, default=8011, help="Orchestrator API port")
    parser.add_argument("--reload", action="store_true", help="Enable backend auto-reload")
    parser.add_argument(
        "--stop-existing",
        action="store_true",
        help="Stop process currently using backend port before starting",
    )
    return parser


def start_process(command: list[str], cwd: Path) -> None:
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_CONSOLE

    subprocess.Popen(command, cwd=str(cwd), creationflags=creationflags)


def open_frontend_url(delay_seconds: float = 6.0) -> None:
    Timer(delay_seconds, lambda: webbrowser.open(FRONTEND_URL, new=2)).start()


def is_local_port_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def start_backend(
    project_root: Path,
    app_name: str,
    port: int,
    reload_enabled: bool,
    stop_existing: bool,
) -> None:
    start_api = project_root / "start-api.ps1"
    if not start_api.exists():
        raise FileNotFoundError(f"Missing startup script: {start_api}")

    command = [
        "powershell",
        "-NoExit",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(start_api),
        "-App",
        app_name,
        "-Port",
        str(port),
    ]

    if reload_enabled:
        command.append("-Reload")
    if stop_existing:
        command.append("-StopExisting")

    print(f"Starting {app_name} API on http://127.0.0.1:{port} ...")
    start_process(command, cwd=project_root)


def start_frontend(project_root: Path) -> None:
    frontend_path = project_root / "frontend"
    if not frontend_path.exists():
        raise FileNotFoundError(f"Missing frontend directory: {frontend_path}")

    if is_local_port_open(3000):
        print(f"Frontend already running on {FRONTEND_URL}. Opening existing dashboard ...")
        webbrowser.open(FRONTEND_URL, new=2)
        return

    command_script = (
        f'Set-Location -Path "{frontend_path}"; '
        "if (-not (Test-Path node_modules)) { npm install }; "
        "npm run dev"
    )

    command = [
        "powershell",
        "-NoExit",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        command_script,
    ]

    print(f"Starting frontend on {FRONTEND_URL} ...")
    start_process(command, cwd=frontend_path)
    open_frontend_url()


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent

    print("\nGigAI Main Launcher (.py)")
    print(f"Launcher version: {LAUNCHER_VERSION}")
    print("Latest updates:")
    for item in LATEST_UPDATES:
        print(f"  - {item}")
    print(f"Mode: {args.mode}\n")

    if args.mode in ("all", "backend"):
        start_backend(
            project_root=project_root,
            app_name="dashboard",
            port=args.backend_port,
            reload_enabled=args.reload,
            stop_existing=args.stop_existing,
        )
        start_backend(
            project_root=project_root,
            app_name="orchestrator",
            port=args.orchestrator_port,
            reload_enabled=args.reload,
            stop_existing=args.stop_existing,
        )

    if args.mode in ("all", "frontend"):
        start_frontend(project_root=project_root)

    print("\nStarted requested services.")
    if args.mode in ("all", "backend"):
        print(f"Dashboard API:    {DASHBOARD_API_URL}/docs")
        print(f"Orchestrator API: {ORCHESTRATOR_API_URL}/docs")
    if args.mode in ("all", "frontend"):
        print(f"Frontend: {FRONTEND_URL}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
