import ntpath
import os
import shutil
import sys
import winreg

APP_ID = "{C1E3E4A4-7D21-4E6B-9C91-CRYXRAXBROWSER}"
APP_NAME = "Manganese"
APP_PUBLISHER = "Mult1c/Cryxcrax"
APP_VERSION = "2.1.0"
EXE_NAME = "Manganesev2.1.0.exe"

DEFAULT_INSTALL_DIR = ntpath.join(
    os.environ.get("ProgramFiles", r"C:\Program Files"), "Cryxcrax", "Manganese"
)


def _program_files_group_dir():
    start_menu = os.path.join(
        os.environ.get("ProgramData", r"C:\ProgramData"),
        "Microsoft", "Windows", "Start Menu", "Programs", APP_NAME,
    )
    return start_menu


def _public_desktop_dir():
    return os.environ.get("PUBLIC", r"C:\Users\Public") + r"\Desktop"


def copy_application_files(source_dir: str, install_dir: str, progress_cb=None):
    os.makedirs(install_dir, exist_ok=True)

    all_files = []
    for root, _dirs, files in os.walk(source_dir):
        for name in files:
            all_files.append(os.path.join(root, name))

    total = len(all_files)
    for i, src_path in enumerate(all_files, start=1):
        rel_path = os.path.relpath(src_path, source_dir)
        dst_path = os.path.join(install_dir, rel_path)
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        shutil.copy2(src_path, dst_path)
        if progress_cb:
            progress_cb(i, total, rel_path)


def prepare_install_directory(install_dir: str):
    install_dir = os.path.abspath(install_dir)
    drive, _tail = os.path.splitdrive(install_dir)
    if os.path.normcase(os.path.normpath(install_dir)) == os.path.normcase(os.path.normpath(drive + os.sep)):
        raise ValueError("Choose an application folder rather than a drive root.")

    import subprocess
    subprocess.run(
        [
            "powershell.exe", "-NoProfile", "-Command",
            "Get-Process | Where-Object { $_.ProcessName -like 'Manganesev*' } | Stop-Process -Force",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    remove_shortcuts()
    if os.path.exists(install_dir):
        shutil.rmtree(install_dir)
    os.makedirs(install_dir, exist_ok=True)


def _create_shortcut_via_wsh(target: str, shortcut_path: str, icon_path: str, working_dir: str):
    import comtypes.client
    from comtypes.client.dynamic import Dispatch


    shell = Dispatch(comtypes.client.CreateObject("WScript.Shell"))
    shortcut = Dispatch(shell.CreateShortcut(shortcut_path))
    shortcut.TargetPath = target
    shortcut.WorkingDirectory = working_dir
    shortcut.IconLocation = icon_path
    shortcut.Save()


def create_shortcuts(install_dir: str, icon_path: str, desktop: bool = True, start_menu: bool = True):
    exe_path = os.path.join(install_dir, EXE_NAME)

    if start_menu:
        group_dir = _program_files_group_dir()
        os.makedirs(group_dir, exist_ok=True)
        _create_shortcut_via_wsh(
            exe_path, os.path.join(group_dir, f"{APP_NAME}.lnk"), icon_path, install_dir
        )

    if desktop:
        try:
            _create_shortcut_via_wsh(
                exe_path, os.path.join(_public_desktop_dir(), f"{APP_NAME}.lnk"), icon_path, install_dir
            )
        except Exception:
            pass


def remove_shortcuts():
    group_dir = _program_files_group_dir()
    shutil.rmtree(group_dir, ignore_errors=True)
    desktop_shortcut = os.path.join(_public_desktop_dir(), f"{APP_NAME}.lnk")
    try:
        os.remove(desktop_shortcut)
    except FileNotFoundError:
        pass


def write_uninstall_registration(install_dir: str, uninstaller_path: str, icon_path: str):
    key_path = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{APP_ID}"
    with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
        winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, APP_PUBLISHER)
        winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, install_dir)
        winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, icon_path)
        winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{uninstaller_path}" --uninstall')
        winreg.SetValueEx(key, "QuietUninstallString", 0, winreg.REG_SZ, f'"{uninstaller_path}" --uninstall --quiet')
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, _estimated_size_kb(install_dir))


def _estimated_size_kb(install_dir: str) -> int:
    total = 0
    for root, _dirs, files in os.walk(install_dir):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    return total // 1024


def remove_uninstall_registration():
    key_path = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{APP_ID}"
    try:
        winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, key_path)
    except (FileNotFoundError, OSError):
        pass


def is_running_as_admin() -> bool:
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin():
    import ctypes
    params = " ".join(f'"{a}"' for a in sys.argv[1:])
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, params, None, 1
    )
    sys.exit(0)
