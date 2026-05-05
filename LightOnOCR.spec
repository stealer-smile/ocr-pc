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

# Collect transformers (AutoConfig, AutoProcessor, GenerationConfig + torch dependency chain)
datas_tf, binaries_tf, hiddenimports_tf = collect_all("transformers")

# Collect tokenizers
datas_tok, binaries_tok, hiddenimports_tok = collect_all("tokenizers")

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[*binaries_ort, *binaries_tf, *binaries_tok],
    datas=[
        *([("assets", "assets")] if os.path.isdir("assets") else []),
        *datas_ort,
        *datas_tf,
        *datas_tok,
        *collect_data_files("pypdfium2"),
        *collect_data_files("tkinterdnd2"),
        *collect_data_files("tkhtmlview"),
        *collect_data_files("docx"),
        *collect_data_files("huggingface_hub"),
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
        "numpy",
        "onnxruntime",
        "huggingface_hub",
        *hiddenimports_ort,
        *hiddenimports_tf,
        *hiddenimports_tok,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
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
