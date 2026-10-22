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
# safehttpx reads its own version.txt at import time (FileNotFoundError
# in frozen builds without it); tzdata is needed by zoneinfo on Windows.
for pkg in ("gradio", "gradio_client", "hf_gradio", "spaces", "huggingface_hub",
            "safehttpx", "tzdata"):
    try:
        datas += collect_data_files(pkg)
    except Exception:
        pass

# --- Generic cure for the "package reads its own version.txt at import time"
# bug class (bit us twice: safehttpx, then groovy). Scan the build environment
# for every installed package that ships a top-level version.txt and bundle it,
# so no future dependency can crash the frozen app this way again.
import glob as _glob
import os as _os
import sys as _sys

_sp = _os.path.join(_sys.prefix, "lib",
                    "python%d.%d" % _sys.version_info[:2], "site-packages")
if not _os.path.isdir(_sp):  # Windows layout, just in case
    _sp = _os.path.join(_sys.prefix, "Lib", "site-packages")
for _vt in _glob.glob(_os.path.join(_sp, "*", "version.txt")):
    _pkg = _os.path.basename(_os.path.dirname(_vt))
    datas.append((_vt, _pkg))
    print("[spec] bundling version.txt for package: %s" % _pkg)

# --- gradio's component_meta.create_or_modify_pyi() re-reads the package's own
# .py sources at import time (to regenerate .pyi stubs). Frozen builds carry
# only compiled bytecode, so ship every gradio source file as data too.
# (collect_data_files/collect_all would NOT help: they skip .py files.)
import gradio as _gradio

_gdir = _os.path.dirname(_gradio.__file__)
_groot = _os.path.dirname(_gdir)
_n = 0
for _root, _dirs, _files in _os.walk(_gdir):
    for _fn in _files:
        if _fn.endswith((".py", ".pyi")):
            datas.append((_os.path.join(_root, _fn),
                          _os.path.relpath(_root, _groot)))
            _n += 1
print("[spec] bundled %d gradio source files" % _n)

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
