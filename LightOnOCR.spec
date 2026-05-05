# -*- mode: python ; coding: utf-8 -*-
"""
build.spec — PyInstaller build configuration for LightOnOCR (ONNX)
Build: pyinstaller build.spec
"""
from PyInstaller.utils.hooks import collect_all, collect_data_files
import os

block_cipher = None

# Collect ONNX Runtime data
datas_ort, binaries_ort, hiddenimports_ort = collect_all("onnxruntime")

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=binaries_ort,
    datas=[
        *([("assets", "assets")] if os.path.isdir("assets") else []),
        *datas_ort,
        *collect_data_files("pypdfium2"),
        *collect_data_files("tkinterdnd2"),
        *collect_data_files("tokenizers"),
        *collect_data_files("tkhtmlview"),
        *collect_data_files("docx"),
    ],
    hiddenimports=[
        "ocr_engine",
        "pdf_processor",
        "config",
        "startup_manager",
        "docx_exporter",
        "tkinterdnd2",
        "tkhtmlview",
        "markdown",
        "docx",
        "lxml",
        "pypdfium2",
        "PIL",
        "PIL._tkinter_finder",
        "transformers",
        "numpy",
        "onnxruntime",
        "huggingface_hub",
        *hiddenimports_ort,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "torch",
        "torch.distributed",
        "triton",
        "matplotlib",
        "numpy.testing",
        "IPython",
        "jupyter",
        "notebook",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="LightOnOCR",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    # icon="assets\\icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="LightOnOCR",
)
