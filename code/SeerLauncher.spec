# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

from PyInstaller.utils.hooks import copy_metadata, collect_dynamic_libs

a = Analysis(
    ['SeerLauncher.py'],
    pathex=['.'],
    binaries=[
        ('SpeedControl.dll', '.'),
        ('ini\\dm.dll', '.'),
        *collect_dynamic_libs('cryptography')
    ],
    datas=[
        *copy_metadata('cryptography'),
        ('img\\logo.ico', 'img')
    ],
    hiddenimports=[
        'cryptography.hazmat.backends',
        'cryptography.hazmat.bindings',
        'cryptography.hazmat.primitives',
        'win32timezone'
    ],
    hookspath=[],
    hooksconfig={
        'cryptography': {
            'crypto_required': True
        }
    },
    runtime_hooks=[],
    excludes=['tkinter', 'test'],
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
    upx_exclude=['vcruntime140.dll'],
    runtime_tmpdir=None,
    console=False,  # 控制台开关在此处设置
    uac_admin=False,  # 以管理员权限打开
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    manifest='|'.join([
        '<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">',
        '<trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">',
        '<security>',
        '<requestedPrivileges>',
        '<requestedExecutionLevel level="requireAdministrator"/>',
        '</requestedPrivileges>',
        '</security>',
        '</trustInfo>',
        '<compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1">',
        '<application>',
        '<supportedOS Id="{35138b9a-5d96-4fbd-8e2d-a2440225f93a}"/>',
        '</application>',
        '</compatibility>',
        '</assembly>'
    ])
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='茶杯登录器',
)