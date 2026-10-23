# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\Mult1c\\Desktop\\cryxcrax-manganese-main (1)\\cryxcrax-manganese-main\\installer\\installer_app.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\Mult1c\\Desktop\\cryxcrax-manganese-main (1)\\cryxcrax-manganese-main\\dist\\installer\\payload', 'payload'), ('C:\\Users\\Mult1c\\Desktop\\cryxcrax-manganese-main (1)\\cryxcrax-manganese-main\\dist\\installer\\assets', 'assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Manganese Setup',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
