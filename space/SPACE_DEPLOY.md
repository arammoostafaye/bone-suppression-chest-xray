# Your own Hugging Face Space (installable PWA)

Deploys this repo to a Space under **your** HF account, running `app_space.py`
— the exact upstream `app.py` plus two launch arguments
(`favicon_path`, `pwa=True`) that make Gradio serve `/manifest.json` and
auto-generate 192/512 PNG icons, so the Space installs to a phone's home
screen as a standalone app.

The GitHub mirror is untouched: `app.py`, `README.md`, `requirements.txt`,
`.gitattributes` and `examples/` stay byte-identical to the upstream Space.
Only the Space's own `README.md` differs, by two frontmatter lines:

```diff
-app_file: app.py
+app_file: app_space.py
-startup_duration_timeout: 30m
+startup_duration_timeout: 15m
```

## Deploy

1. Create a token with the **write** scope at
   https://huggingface.co/settings/tokens
2. From the repo root:

```bash
pip install huggingface_hub
export HF_TOKEN=hf_...
python space/deploy_space.py            # private Space (default)
# python space/deploy_space.py --public # if you want a shareable URL
```

It creates `<you>/bone-suppression-chest-xray`, uploads the Space layout and
requests the `zero-a10g` (ZeroGPU) hardware the upstream Space uses. Re-running
is safe — it just re-uploads.

## Install as a PWA

- **Android / Chrome:** open the Space URL → menu ⋮ → *Add to Home screen* /
  *Install app*.
- **iOS / Safari:** open the URL → Share → *Add to Home Screen*.
- **Desktop Chrome/Edge:** install icon at the right of the address bar.

The icon comes from `desktop/icon.png`; Gradio derives the 192/512 manifest
icons from it at runtime (verified: `/manifest.json` returns
`display: standalone` with both icon sizes).

There is intentionally **no service worker / offline mode**: inference runs on
the Space's GPU, so an offline copy would be a dead UI. The PWA value here is
installability, the standalone window and the icon.

## Notes

- **Private by default** protects your ZeroGPU quota from strangers. A private
  Space asks you to sign in on first open — sign in once on the phone and the
  installed PWA keeps the session.
- ZeroGPU on a free personal account is quota-limited per day; heavy use may
  queue. `--hardware none` skips the request if you prefer CPU-free setup and
  will set it manually in Space Settings.
- The weights are **not** stored in the Space: `app_space.py` downloads them
  from `qureaiorg/bone-suppression` at startup, exactly like upstream.
- Licence unchanged: CC BY-NC-SA 4.0, non-commercial, attribution to Qure.ai.
