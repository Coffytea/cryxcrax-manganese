import os
import sys

from PyQt6.QtWidgets import QApplication, QMessageBox

import install_logic
import win_registration


def _installed_dir_from_self():
    """Directory this uninstaller is running from. sys.argv[0] is not
    reliable for a frozen exe (it can be relative, or not match how the
    OS actually launched the process, e.g. via the registry's
    UninstallString) -- use sys.executable when frozen instead."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(sys.argv[0]))


def run_uninstall(quiet: bool = False, purge_data: bool = False):
    if not install_logic.is_running_as_admin():
        install_logic.relaunch_as_admin()
        return

    install_dir = _installed_dir_from_self()

    if not quiet:
        app = QApplication(sys.argv)
        reply = QMessageBox.question(
            None, "Uninstall Manganese",
            f"Remove Manganese from your computer?\n\n{install_dir}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

    win_registration.unregister_as_browser()
    install_logic.remove_shortcuts()
    install_logic.remove_uninstall_registration()

    import subprocess
    app_data_dir = os.path.join(
        os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "Manganese"
    )
    subprocess.run(
        [
            "powershell.exe", "-NoProfile", "-Command",
            "Get-Process | Where-Object { $_.ProcessName -like 'Manganesev*' } | Stop-Process -Force",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    _schedule_self_delete(install_dir, app_data_dir, os.getpid())


def _schedule_self_delete(install_dir: str, app_data_dir: str, process_id: int):
    import subprocess

    parent_dir = os.path.dirname(install_dir)
    log_path = os.path.join(os.environ.get("TEMP", os.path.expanduser("~")), "manganese_uninstall.log")
    quote = lambda value: "'" + value.replace("'", "''") + "'"
    command = (
        "$ErrorActionPreference='Continue'; "
        f"$targets=@({quote(install_dir)},{quote(app_data_dir)}); "
        f"$parent={quote(parent_dir)}; $log={quote(log_path)}; $owner={process_id}; "
        "while (Get-Process -Id $owner -ErrorAction SilentlyContinue) { Start-Sleep -Milliseconds 500 }; "
        "for ($attempt=0; $attempt -lt 180; $attempt++) { "
        "foreach ($target in $targets) { "
        "if (Test-Path -LiteralPath $target) { "
        "try { Remove-Item -LiteralPath $target -Recurse -Force -ErrorAction Stop } "
        "catch { Add-Content -LiteralPath $log -Value $_.Exception.Message } } }; "
        "$remaining=$false; foreach ($target in $targets) { "
        "if (Test-Path -LiteralPath $target) { $remaining=$true } }; "
        "if (-not $remaining) { exit 0 }; "
        "Start-Sleep -Seconds 1 }; "
        "Add-Content -LiteralPath $log -Value ('Failed to remove: ' + "
        "(@($targets | Where-Object { Test-Path -LiteralPath $_ }) -join '; '))"
    )
    subprocess.Popen(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-Command", command],
        creationflags=subprocess.CREATE_NO_WINDOW,
        close_fds=True,
    )


if __name__ == "__main__":
    run_uninstall(quiet="--quiet" in sys.argv, purge_data="--purge-data" in sys.argv)
