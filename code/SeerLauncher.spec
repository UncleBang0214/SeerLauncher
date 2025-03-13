# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

from PyInstaller.utils.hooks import copy_metadata, collect_dynamic_libs

a = Analysis(
    ['SeerLauncher.py'],
    pathex=['.'],
    binaries=[
        ('ini\\s.dll', 'ini'),
        ('ini\\d.dll', 'ini'),
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
        'win32timezone',
        'sip',
        'PyQt5.sip'
    ],
    hookspath=[],
    hooksconfig={
        'cryptography': {
            'crypto_required': True
        }
    },
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'test',
        'PyQt5.Qt3D*',       # 排除3D模块
        'PyQt5.QtMultimedia',# 排除多媒体
        'PyQt5.QtSensors',   # 排除传感器
        'PyQt5.QtPositioning'# 排除定位
    ],
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
    upx=False,
    upx_options=['--best', '--lzma'],
    upx_exclude=[
        'vcruntime140.dll'
    ],
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
