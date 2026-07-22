import os
import shutil
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

    if purge_data:
        from manganese.paths import app_data_dir
        shutil.rmtree(app_data_dir(), ignore_errors=True)

    _schedule_self_delete(install_dir)

    if not quiet:
        QMessageBox.information(None, "Manganese removed", "Manganese has been removed from your computer.")


def _schedule_self_delete(install_dir: str):
    """Delete install_dir after this process exits. Runs as a detached
    cmd.exe so it survives this process ending (needed since install_dir
    contains the running uninstall.exe -- it can't delete its own folder
    while still executing from it). Retries several times since the OS
    may briefly hold the exe's file handle open right after exit, and
    logs to install_dir's parent so a failure is actually visible instead
    of silently leaving files behind.

    NOTE: %%i (not %i) is required for the FOR loop variable here. %i is
    only correct inside a .bat *file*; cmd.exe run via `cmd /c "..."`
    needs the variable doubled, or it gets consumed/mis-expanded by the
    parser before FOR ever runs -- which silently broke this whole loop.
    """
    import subprocess
    parent_dir = os.path.dirname(install_dir)
    log_path = os.path.join(parent_dir, "manganese_uninstall.log")
    cmd = (
        f'for /L %%i in (1,1,10) do ('
        f'  rmdir /s /q "{install_dir}" 2>nul'
        f'  if not exist "{install_dir}" exit /b 0'
        f'  ping 127.0.0.1 -n 2 > nul'
        f')'
        f' & if exist "{install_dir}" ('
        f'   echo Failed to remove "{install_dir}" after 10 attempts. > "{log_path}"'
        f' )'
    )
    subprocess.Popen(
        ["cmd.exe", "/c", cmd],
        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
        close_fds=True,
    )


if __name__ == "__main__":
    run_uninstall(quiet="--quiet" in sys.argv, purge_data="--purge-data" in sys.argv)
