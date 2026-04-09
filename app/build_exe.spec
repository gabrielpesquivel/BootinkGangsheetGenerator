# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Shopify Gang Sheet Generator
Run from app/ folder: python -m PyInstaller build_exe.spec --noconfirm
"""

import sys
import os
import shutil
from pathlib import Path

# Get tkinterdnd2 path for bundling
import tkinterdnd2
tkdnd_path = Path(tkinterdnd2.__file__).parent

# Get paths relative to this spec file
SPEC_DIR = Path(SPECPATH).resolve()
ROOT_DIR = SPEC_DIR.parent

block_cipher = None

# Locate rsvg-convert so PyInstaller bundles it (and its shared libs)
_rsvg_bin = shutil.which('rsvg-convert')
_rsvg_binaries = [(_rsvg_bin, '.')] if _rsvg_bin else []

# Platform detection
is_macos = sys.platform == 'darwin'

# Icon: use .ico on Windows, skip on macOS (no .icns available)
icon_file = None if is_macos else str(ROOT_DIR / 'assets' / 'bootinkLogo.ico')

# Modules to exclude for smaller size (conservative list)
excluded_modules = [
    # Testing frameworks
    'pytest', '_pytest', 'pluggy',
    # IPython/Jupyter
    'IPython', 'ipykernel', 'jupyter', 'notebook', 'ipywidgets',
    # Unused scientific packages
    'scipy', 'sympy', 'statsmodels', 'sklearn', 'skimage',
]

a = Analysis(
    ['gui.py'],
    pathex=[str(SPEC_DIR)],
    binaries=_rsvg_binaries,
    datas=[
        # Include assets folder from root
        (str(ROOT_DIR / 'assets'), 'assets'),
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
    excludes=excluded_modules,
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
    name='Bootink Sheet Tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Disable UPX - faster startup (no decompression needed)
    upx_exclude=[],
    runtime_tmpdir=None,  # Use system temp directory (avoids cache folder on desktop)
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=is_macos,  # Required for macOS GUI apps
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)
