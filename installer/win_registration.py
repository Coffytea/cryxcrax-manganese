import winreg


APP_NAME = "Manganese"
APP_DESCRIPTION = "Manganese -- a fast, modern web browser."


def register_as_browser(install_dir: str, exe_name: str = "Manganesev2.0.exe"):
    exe_path = f"{install_dir}\\{exe_name}"
    icon_path = f"{exe_path},0"
    client_key_path = rf"Software\Clients\StartMenuInternet\{APP_NAME}"

    with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, client_key_path) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, APP_NAME)
        winreg.SetValueEx(key, "LocalizedString", 0, winreg.REG_SZ, APP_NAME)

    with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, client_key_path + r"\DefaultIcon") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, icon_path)

    with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, client_key_path + r"\shell\open\command") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f'"{exe_path}"')

    capabilities_path = client_key_path + r"\Capabilities"
    with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, capabilities_path) as key:
        winreg.SetValueEx(key, "ApplicationName", 0, winreg.REG_SZ, APP_NAME)
        winreg.SetValueEx(key, "ApplicationDescription", 0, winreg.REG_SZ, APP_DESCRIPTION)
        winreg.SetValueEx(key, "ApplicationIcon", 0, winreg.REG_SZ, icon_path)

    with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, capabilities_path + r"\URLAssociations") as key:
        winreg.SetValueEx(key, "http", 0, winreg.REG_SZ, f"{APP_NAME}HTML")
        winreg.SetValueEx(key, "https", 0, winreg.REG_SZ, f"{APP_NAME}HTML")

    with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, capabilities_path + r"\FileAssociations") as key:
        winreg.SetValueEx(key, ".htm", 0, winreg.REG_SZ, f"{APP_NAME}HTML")
        winreg.SetValueEx(key, ".html", 0, winreg.REG_SZ, f"{APP_NAME}HTML")

    progid_path = rf"Software\Classes\{APP_NAME}HTML"
    with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, progid_path) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f"{APP_NAME} Document")

    with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, progid_path + r"\DefaultIcon") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, icon_path)

    with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, progid_path + r"\shell\open\command") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f'"{exe_path}" "%1"')

    with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, r"Software\RegisteredApplications") as key:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, capabilities_path)

    _broadcast_settings_change()


def unregister_as_browser():
    def _delete_tree(root, path):
        try:
            with winreg.OpenKey(root, path, 0, winreg.KEY_ALL_ACCESS) as key:
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, 0)
                    except OSError:
                        break
                    _delete_tree(root, path + "\\" + subkey_name)
            winreg.DeleteKey(root, path)
        except FileNotFoundError:
            pass
        except OSError:
            pass

    _delete_tree(winreg.HKEY_LOCAL_MACHINE, rf"Software\Clients\StartMenuInternet\{APP_NAME}")
    _delete_tree(winreg.HKEY_LOCAL_MACHINE, rf"Software\Classes\{APP_NAME}HTML")

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"Software\RegisteredApplications",
                             0, winreg.KEY_ALL_ACCESS) as key:
            winreg.DeleteValue(key, APP_NAME)
    except (FileNotFoundError, OSError):
        pass

    _broadcast_settings_change()


def _broadcast_settings_change():
    try:
        import ctypes
        HWND_BROADCAST = 0xFFFF
        WM_SETTINGCHANGE = 0x001A
        SMTO_ABORTIFHUNG = 0x0002
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST, WM_SETTINGCHANGE, 0,
            "Software\\Clients\\StartMenuInternet",
            SMTO_ABORTIFHUNG, 5000, None,
        )
    except Exception:
        pass
