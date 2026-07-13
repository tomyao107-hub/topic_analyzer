# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

datas, binaries, hiddenimports = [], [], []
for package in ("wordcloud", "pyLDAvis"):
    datas += collect_data_files(package)
    binaries += collect_dynamic_libs(package)

# rpy2 remains optional at runtime, but include its Python modules so packaged STM
# works when the user has installed R and the R package stm.
hiddenimports += [
    "gensim.models.ldamodel", "gensim.models.coherencemodel", "pyLDAvis.gensim_models",
    "rpy2.robjects", "rpy2.robjects.packages", "rpy2.rinterface_lib.openrlib",
]

analysis = Analysis(
    ["backend/sidecar_entry.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={"matplotlib": {"backends": ["Agg"]}},
    runtime_hooks=[],
    excludes=["PySide6", "tkinter"],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="topic-analyzer-backend-x86_64-pc-windows-msvc",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)
