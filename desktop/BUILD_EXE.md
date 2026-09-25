# Building the Windows `.exe`

Personal-use desktop build of the bone-suppression demo. `app.py` (the upstream
mirror) is untouched; this builds from `app_codespaces.py`, which picks the
device at runtime, so the exe runs on **CPU** out of the box and on an NVIDIA
GPU if you build with CUDA torch.

New files (nothing mirrored was changed):

| File | Purpose |
|---|---|
| `desktop/run_desktop.py` | entry point: starts Gradio on a free localhost port, opens a native window (pywebview/WebView2), falls back to the default browser |
| `desktop/bone_suppression.spec` | PyInstaller spec (onedir, ~1–1.3 GB, `console=False`, logs to `bone-suppression.log`) |
| `desktop/icon.ico` / `icon.png` | app icon + Gradio favicon |
| `.github/workflows/build-windows.yml` | builds on a GitHub `windows-latest` runner and uploads the zip |

## What you get

- `dist/BoneSuppression/BoneSuppression.exe` (onedir — the whole folder is the app)
- Zipped for transport: `BoneSuppression-Windows-x64.zip`
- **The 797 MB of weights are NOT inside the exe.** On first launch they are
  downloaded from `qureaiorg/bone-suppression` into
  `%USERPROFILE%\.cache\huggingface`. This keeps the build under GitHub's 2 GiB
  release-asset limit.

Requirements on the target machine: Windows 10/11 x64, **8 GB RAM minimum**
(both traces are ~1.4 GB resident before activations), ~2 GB free disk for the
app plus ~1 GB for the weight cache. No GPU needed.

## Route A — GitHub builds it for you (recommended, no Windows toolchain)

1. Push these files (already done by the commit that added them).
2. On GitHub: **Actions** tab → **Build Windows exe** → **Run workflow** → green **Run workflow**.
3. Wait ~15–30 min. Open the run → **Artifacts** → download `BoneSuppression-Windows-x64`.
4. Unzip anywhere, double-click `BoneSuppression.exe`.

Artifacts expire after 90 days. For a permanent link, tag a release:

```bash
git tag v1.0.0 && git push origin v1.0.0
```

The same workflow then also publishes the zip as a **Release** asset.

## Route B — build on your own Windows machine

Prereqs: Python 3.12 from python.org, and a repo checkout.

```powershell
cd bone-suppression-chest-xray
python -m venv .venv ; .\.venv\Scripts\Activate.ps1

# CPU build (default, ~200 MB download)
pip install --index-url https://download.pytorch.org/whl/cpu torch
#   ...or, if you have an NVIDIA GPU and want GPU speed (~2.5 GB download):
# pip install torch

pip install -r .devcontainer\requirements-codespaces.txt
pip install pyinstaller pywebview

pyinstaller desktop\bone_suppression.spec --noconfirm --clean
```

Result: `dist\BoneSuppression\BoneSuppression.exe`.

## First launch

1. A native window opens (Edge WebView2). If pywebview cannot start, your
   default browser opens instead.
2. First run downloads ~800 MB of weights — expect a blank window for a while.
   Subsequent launches start in seconds from the cache.
3. Pick an example image or upload your own PA/AP radiograph, press **Decompose**.
   On CPU expect roughly a minute or more per image; with CUDA torch, seconds.

Quit by closing the window (or the console, in a source run).

## Troubleshooting

| Symptom | Fix |
|---|---|
| Nothing appears, no window | `console=False` hides stdout. Read `bone-suppression.log` next to the exe. To get a live console, set `console=True` in `desktop/bone_suppression.spec` and rebuild. |
| Window opens blank for minutes | first-run weight download, or slow CPU inference. Watch `bone-suppression.log`. |
| Killed / crashes on a big image | not enough RAM. Close other apps; the two traces need ~1.4 GB plus several GB of activations at 1024×1024. |
| Port clash | the launcher picks a free port automatically (`BSP_PORT` env var to force one). |
| Want it on the GPU | build with the CUDA wheel (Route B, commented line) — `app_codespaces.py` uses CUDA when `torch.cuda.is_available()`. |

## Why not `onefile`?

A single-file exe would unpack ~1.3 GB to a temp dir on **every** start (slow,
and antivirus-hostile). `onedir` starts instantly and is the PyInstaller
recommendation for apps of this size.

## Licence

Unchanged from `README.md`: weights are **CC BY-NC-SA 4.0** — non-commercial,
share-alike, attribution to Qure.ai. This personal-use build is fine; do not
redistribute it commercially. Research software, not a medical device.
