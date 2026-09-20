# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['TimeClock_1.0.1.py'],
    pathex=[],
    binaries=[],
    datas=[('time.ico', '.')],
    hiddenimports=['windows_toasts', 'winrt', 'winrt.windows.ui.notifications', 'winrt.windows.foundation', 'winrt.windows.foundation.collections', 'winrt.windows.data.xml.dom'],
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
    [],
    exclude_binaries=True,
    name='TimeClock',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['time.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TimeClock',
)
