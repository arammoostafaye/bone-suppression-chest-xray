# PyInstaller spec for the Windows desktop build.
#
# Build (from the repo root):
#     pyinstaller desktop/bone_suppression.spec --noconfirm --clean
# Output:
#     dist/BoneSuppression/BoneSuppression.exe   (onedir, ~1-1.3 GB)
#
# The 797 MB of model weights are deliberately NOT bundled: they are fetched
# from qureaiorg/bone-suppression by huggingface_hub on first launch and cached
# in %USERPROFILE%\.cache\huggingface, which keeps this build under GitHub's
# 2 GiB release-asset limit.

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = os.path.abspath(os.path.join(SPECPATH, os.pardir))

# ---------------------------------------------------------------------------
# Data files
# ---------------------------------------------------------------------------
# gr.Examples() in app_codespaces.py resolves "examples/..." against the CWD,
# which run_desktop.py sets to the bundle root. The PNG is Gradio's favicon.
datas = [
    (os.path.join(ROOT, "examples"), "examples"),
    (os.path.join(ROOT, "desktop", "icon.png"), os.path.join("desktop")),
]

# Gradio ships its built frontend as package data that static analysis misses.
for pkg in ("gradio", "gradio_client", "hf_gradio", "spaces", "huggingface_hub"):
    try:
        datas += collect_data_files(pkg)
    except Exception:
        pass  # optional / absent in some environments

icon_path = os.path.join(ROOT, "desktop", "icon.ico")
icon = icon_path if os.path.exists(icon_path) else None

# ---------------------------------------------------------------------------
# Hidden imports
# ---------------------------------------------------------------------------
# app_codespaces is imported after a runtime sys.path tweak, so PyInstaller
# cannot see it statically.
hiddenimports = ["app_codespaces", "spaces", "webview", "clr"]

for pkg in ("gradio", "gradio_client", "webview", "spaces"):
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Excludes - trims ~200 MB without touching anything the app imports.
# sympy is kept: torch imports it. tkinter is kept: harmless and tiny.
# ---------------------------------------------------------------------------
excludes = [
    "torch.test",            # 85 MB of torch's own test suite
    "matplotlib", "IPython", "jupyter", "notebook", "jupyterlab",
    "pytest", "sphinx", "pandas.tests", "numpy.tests",
    "PyQt5", "PyQt6", "PySide2", "PySide6",   # pywebview uses WebView2 on Windows
    "tensorflow", "onnx", "onnxruntime",
]

a = Analysis(
    ["run_desktop.py"],
    pathex=[ROOT, os.path.join(ROOT, "desktop")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BoneSuppression",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                 # UPX corrupts torch's native DLLs - keep it off
    console=False,             # no console window; logs go to bone-suppression.log
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
    version=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="BoneSuppression",
)
