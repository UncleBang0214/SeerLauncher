# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['SeerLauncher.py'],
    pathex=[],
    binaries=[
        ('SpeedControl.dll', '.'),
        ('dm.dll', '.')
    ],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='茶杯登录器',
    icon='img\\logo.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # 启动exe时不打开控制台
    uac_admin=False,  # 强制以管理员权限运行
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None
)