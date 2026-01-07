# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Shopify Gang Sheet Generator
Run with: pyinstaller build_exe.spec
"""

import sys
from pathlib import Path

# Get tkinterdnd2 path for bundling
import tkinterdnd2
tkdnd_path = Path(tkinterdnd2.__file__).parent

block_cipher = None

a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include assets folder
        ('assets', 'assets'),
        # Include tkinterdnd2 library files
        (str(tkdnd_path), 'tkinterdnd2'),
    ],
    hiddenimports=[
        'tkinterdnd2',
        'customtkinter',
        'pandas',
        'numpy',
        'shapely',
        'shapely.geometry',
        'reportlab',
        'reportlab.graphics',
        'reportlab.lib',
        'svglib',
        'svglib.svglib',
        'lxml',
        'lxml.etree',
        'PIL',
        'PIL.Image',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='GangSheetGenerator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if you have one: icon='icon.ico'
)
