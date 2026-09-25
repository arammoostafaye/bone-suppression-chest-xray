"""Windows desktop entry point for the bone-suppression demo.

Loads the Gradio app from ``app_codespaces.py`` (the device-agnostic variant of
the upstream ``app.py``), starts it on a free localhost port and shows it in a
native window (pywebview / Edge WebView2) - falling back to the default browser
if pywebview is unavailable.

Nothing here changes the model, the preprocessing contract or the UI: this file
only owns the "run it as a desktop app" part.

Run from source:
    python desktop/run_desktop.py

Frozen with PyInstaller (see bone_suppression.spec):
    dist/BoneSuppression/BoneSuppression.exe
"""

from __future__ import annotations

import logging
import os
import socket
import sys
import threading
import time
import webbrowser

# ---------------------------------------------------------------------------
# Paths. When frozen, everything (module + examples/) lives in sys._MEIPASS.
# gr.Examples() resolves "examples/..." against the CWD, so chdir is required.
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    ROOT = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
else:
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)

# Log next to the exe when frozen (console=False hides stdout); else stderr.
if getattr(sys, "frozen", False):
    _log_path = os.path.join(os.path.dirname(sys.executable), "bone-suppression.log")
    try:
        logging.basicConfig(filename=_log_path, level=logging.INFO, filemode="w",
                            format="%(asctime)s %(levelname)s %(message)s")
    except OSError:
        logging.basicConfig(level=logging.INFO)
else:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("desktop")

# Imported after the sys.path fix above. This triggers the model download and
# the torch.jit.load of both traces (module scope in app_codespaces).
log.info("loading app from %s", ROOT)
import app_codespaces  # noqa: E402

APP_NAME = "Bone Suppression — Chest X-ray"
HOST = "127.0.0.1"


def free_port() -> int:
    """Ask the OS for an unused TCP port (avoids clashing with a running Space)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, 0))
        return s.getsockname()[1]


def wait_ready(port: int, timeout: float = 120.0) -> bool:
    """Block until the Gradio server accepts connections on `port`."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((HOST, port), timeout=1.0):
                return True
        except OSError:
            time.sleep(0.25)
    return False


def show_native_window(url: str) -> bool:
    """Open a frameless-ish native window. Returns False if pywebview is unusable."""
    try:
        import webview  # pywebview; on Windows this is Edge WebView2
    except Exception as exc:  # pragma: no cover - depends on the bundle
        log.warning("pywebview unavailable (%r); falling back to the browser", exc)
        return False
    try:
        webview.create_window(APP_NAME, url, width=1280, height=940,
                              min_size=(900, 640), resizable=True)
        # Blocks until the last window closes -> the process then exits cleanly.
        webview.start(debug=False)
        return True
    except Exception as exc:  # pragma: no cover
        log.warning("native window failed (%r); falling back to the browser", exc)
        return False


def main() -> int:
    port = int(os.environ.get("BSP_PORT", "0")) or free_port()
    url = f"http://{HOST}:{port}/"

    print(f"[startup] loading the two TorchScript traces (~800 MB on first run)...",
          flush=True)
    log.info("starting gradio on %s", url)

    # prevent_thread_lock -> launch() returns and the server keeps running in
    # Gradio's own thread, so we stay in control of the window lifecycle.
    # `favicon_path`/`pwa` exist in gradio >= 6; the icon is bundled by the spec.
    _icon = os.path.join(ROOT, "desktop", "icon.png")
    if not os.path.exists(_icon):
        _icon = os.path.join(ROOT, "icon.png")
    app_codespaces.demo.launch(
        server_name=HOST,
        server_port=port,
        share=False,
        prevent_thread_lock=True,
        inbrowser=False,
        quiet=True,
        favicon_path=_icon if os.path.exists(_icon) else None,
        pwa=True,   # lets the same build double as an installable PWA later
    )

    if not wait_ready(port):
        log.error("server did not come up on %s within the timeout", url)
        print("[error] the local server did not start; see bone-suppression.log",
              flush=True)
        return 1

    print(f"[ready] {url}", flush=True)
    log.info("server ready at %s", url)

    if show_native_window(url):
        return 0

    # Fallback: default browser, then keep the process alive.
    webbrowser.open(url)
    print("[ready] opened in your default browser. Close this window to quit.",
          flush=True)
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    # Surface a readable dialog-less error in the log file, then a non-zero exit.
    try:
        sys.exit(main())
    except Exception:  # pragma: no cover
        log.exception("fatal")
        import traceback
        traceback.print_exc()
        if not getattr(sys, "frozen", False):
            raise
        # Frozen with console=False: keep the window open long enough to read it.
        time.sleep(30)
        sys.exit(1)
