# Single-file (onefile) Windows build: one BoneSuppression.exe, no zip, no
# extraction by the user. PyInstaller packs everything inside the exe and
# self-extracts to %TEMP% at launch (first start is slower; that is the
# trade-off for a single distributable file).
#
# Build:  pyinstaller desktop/bone_suppression_onefile.spec --noconfirm
# Output: dist/BoneSuppression.exe  (~270 MB, standalone)

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = os.path.abspath(os.path.join(SPECPATH, os.pardir))

datas = [
    (os.path.join(ROOT, "examples"), "examples"),
    (os.path.join(ROOT, "desktop", "icon.png"), os.path.join("desktop")),
]
for pkg in ("gradio", "gradio_client", "hf_gradio", "spaces", "huggingface_hub"):
    try:
        datas += collect_data_files(pkg)
    except Exception:
        pass

icon_path = os.path.join(ROOT, "desktop", "icon.ico")
icon = icon_path if os.path.exists(icon_path) else None

hiddenimports = ["app_codespaces", "spaces", "webview", "clr"]
for pkg in ("gradio", "gradio_client", "webview", "spaces"):
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception:
        pass

excludes = [
    "torch.test",
    "matplotlib", "IPython", "jupyter", "notebook", "jupyterlab",
    "pytest", "sphinx", "pandas.tests", "numpy.tests",
    "PyQt5", "PyQt6", "PySide2", "PySide6",
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

# onefile: binaries and datas go INTO the EXE; there is deliberately no COLLECT.
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="BoneSuppression",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,              # UPX corrupts torch's native DLLs - keep it off
    upx_exclude=[],
    runtime_tmpdir=None,    # self-extract to %TEMP%\<random> at launch
    console=False,          # logs go to bone-suppression.log next to the exe
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)
