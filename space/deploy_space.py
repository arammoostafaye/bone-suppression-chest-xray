#!/usr/bin/env python3
"""Deploy this repo to YOUR OWN Hugging Face Space as an installable PWA.

Creates (or reuses) a Gradio Space under your HF account, uploads the Space
layout built from the mirror files, points `app_file` at `app_space.py`
(app.py + favicon/pwa only), and requests the zero-a10g (ZeroGPU) hardware the
upstream Space uses.

Usage:
    export HF_TOKEN=hf_...                 # write scope
    python space/deploy_space.py

    # or
    python space/deploy_space.py --token hf_... --repo bone-suppression-chest-xray --public

What lands in the Space (nothing in the GitHub mirror is modified):
    README.md           mirror README with app_file rewritten to app_space.py
    app_space.py        app.py + favicon_path/pwa=True (GPU path untouched)
    app.py              the exact upstream mirror, kept for reference
    requirements.txt    as upstream
    examples/           the six sample radiographs
    desktop/icon.png    PWA icon source (gradio derives 192/512 from it)
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build_space_tree(dst: Path) -> None:
    """Assemble the Space layout in `dst` from the repo's mirror files."""
    shutil.copytree(ROOT / "examples", dst / "examples")
    (dst / "desktop").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "desktop" / "icon.png", dst / "desktop" / "icon.png")
    for name in ("app_space.py", "app.py", "requirements.txt"):
        shutil.copy2(ROOT / name, dst / name)

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    old = "app_file: app.py"
    if old not in readme:
        sys.exit(f"expected '{old}' in README.md frontmatter - mirror changed?")
    readme = readme.replace(old, "app_file: app_space.py", 1)
    # A personal Space does not need the 30 min ZeroGPU warm-up budget.
    readme = readme.replace("startup_duration_timeout: 30m", "startup_duration_timeout: 15m")
    (dst / "README.md").write_text(readme, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--token", default=None, help="HF token (write). Default: $HF_TOKEN")
    ap.add_argument("--repo", default="bone-suppression-chest-xray",
                    help="Space name under your account")
    ap.add_argument("--public", action="store_true",
                    help="create the Space publicly (default: private)")
    ap.add_argument("--hardware", default="zero-a10g",
                    help="ZeroGPU flavour; 'none' to skip the request")
    args = ap.parse_args()

    token = args.token or __import__("os").environ.get("HF_TOKEN")
    if not token:
        sys.exit("no token: set HF_TOKEN or pass --token (get one at "
                 "https://huggingface.co/settings/tokens with the 'write' scope)")

    from huggingface_hub import HfApi

    api = HfApi(token=token)
    who = api.whoami()
    user = who["name"]
    repo_id = f"{user}/{args.repo}"
    print(f"[deploy] HF user        : {user}")
    print(f"[deploy] Space          : {repo_id} (private={not args.public})")

    api.create_repo(repo_id, repo_type="space", space_sdk="gradio",
                    private=not args.public, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="space-") as tmp:
        dst = Path(tmp)
        build_space_tree(dst)
        print(f"[deploy] uploading {sum(p.is_file() for p in dst.rglob('*'))} files ...")
        api.upload_folder(folder_path=str(dst), repo_id=repo_id, repo_type="space")

    if args.hardware and args.hardware != "none":
        try:
            api.request_space_hardware(repo_id, args.hardware)
            print(f"[deploy] hardware       : requested {args.hardware}")
        except Exception as exc:  # quota / plan dependent
            print(f"[deploy] hardware request failed ({exc}); set it in Space Settings")

    url = f"https://huggingface.co/spaces/{repo_id}"
    print(f"\n[done] Space : {url}")
    print("[done] PWA    : open it on your phone, then browser menu -> 'Add to Home screen'")
    print("               (gradio serves /manifest.json + 192/512 icons from desktop/icon.png)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
