# Copyright 2026 Mult1c

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://apache.org

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
BROWSER_BUILD_DIR = os.path.join(DIST, "browser_build")
INSTALLER_DIST_DIR = os.path.join(DIST, "installer")
PAYLOAD_DIR = os.path.join(INSTALLER_DIST_DIR, "payload")
ASSETS_DIR = os.path.join(INSTALLER_DIST_DIR, "assets")


def _run(cmd, cwd=None):
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def build_browser():
  
    print("\n=== Building Manganese browser ===")
    icon_path = os.path.join(ROOT, "installer", "assets", "cryx.ico")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--name", "Manganesev2.0",
        "--windowed",
        "--distpath", BROWSER_BUILD_DIR,
        "--workpath", os.path.join(DIST, "_work_browser"),
        "-p", ROOT,
    ]
    if os.path.isfile(icon_path):
        cmd += ["--icon", icon_path]
    else:
        print(f"NOTE: {icon_path} not found -- Manganesev2.0.exe will use "
              f"PyInstaller's default icon.")
    cmd.append(os.path.join(ROOT, "manganese", "__main__.py"))
    _run(cmd, cwd=ROOT)


def build_installer():
   
    print("\n=== Building installer ===")
    installer_dir = os.path.join(ROOT, "installer")
    _run([
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--name", "Manganese Setup",
        "--onefile", "--windowed",
        "--distpath", INSTALLER_DIST_DIR,
        "--workpath", os.path.join(DIST, "_work_installer"),
        os.path.join(installer_dir, "installer_app.py"),
    ], cwd=installer_dir)


def assemble_payload():
    
    print("\n=== Assembling installer payload ===")
    built_browser_dir = os.path.join(BROWSER_BUILD_DIR, "Manganesev2.0")
    if not os.path.isdir(built_browser_dir):
        raise SystemExit(f"Expected built browser at {built_browser_dir}, but it's missing")

    if os.path.isdir(PAYLOAD_DIR):
        shutil.rmtree(PAYLOAD_DIR)
    shutil.copytree(built_browser_dir, PAYLOAD_DIR)
    print(f"Payload assembled at {PAYLOAD_DIR}")

    os.makedirs(ASSETS_DIR, exist_ok=True)
    for asset_name in ("cryx.ico", "Syne-Bold.ttf"):
        src = os.path.join(ROOT, "installer", "assets", asset_name)
        dst = os.path.join(ASSETS_DIR, asset_name)
        if os.path.isfile(src) and os.path.abspath(src) != os.path.abspath(dst):
            shutil.copy2(src, dst)
        elif not os.path.isfile(dst):
            print(f"NOTE: {asset_name} not found -- installer will use a fallback.")


def main():
    if sys.platform != "win32":
        print("This build script produces Windows executables and must be run on Windows.")
        sys.exit(1)

    os.makedirs(DIST, exist_ok=True)
    build_browser()
    build_installer()
    assemble_payload()
    print(f"\nDone. Ship the folder: {INSTALLER_DIST_DIR}")
    print('(Contains "Manganese Setup.exe", assets/, and payload/ -- all three are required together.)')


if __name__ == "__main__":
    main()
