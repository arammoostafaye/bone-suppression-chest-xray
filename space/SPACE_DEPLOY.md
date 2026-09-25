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

### Why the hardware is requested AT creation (the 402 trap)

Since 2026, hosting a Gradio or Docker Space on the free `cpu-basic` flavour
requires an HF **PRO** subscription — creating without a hardware choice fails
with `HTTP 402 Payment Required`. ZeroGPU flavours (`zero-a10g`) remain free
with a daily quota, so `deploy_space.py` passes `space_hardware` to
`create_repo()`. Creating first and switching later is rejected; if you ever
see the 402, the Space was created on the wrong flavour — delete it and re-run.

## Install as a PWA

Install from the **direct app URL**, not from the huggingface.co page:

```
https://<you>-<space-name>.hf.space/
```

- **Android / Chrome:** open that URL → menu ⋮ → *Install app* / *Add to Home screen*.
- **iOS / Safari:** open that URL → Share → *Add to Home Screen*.
- **Desktop Chrome/Edge:** install icon at the right of the address bar.

### Why the direct URL matters (the iframe trap)

`huggingface.co/spaces/<you>/<name>` embeds the app in an **iframe**. Chrome only
offers the install prompt for the **top-level** document, so installing from the
huggingface.co page targets the huggingface.co site itself - which is what sends
Android to the Play store. The `*.hf.space` host is the app's own origin and is
the one that carries the manifest and service worker. (`*.hf.app` no longer
resolves in public DNS; do not use it.)

### What makes it installable (all served by the Space, verified live)

| Endpoint | Purpose |
|---|---|
| `/manifest.json` | name, `display: standalone`, `start_url`, 192/512 icons |
| `/pwa_icon/192`, `/pwa_icon/512` | PNG icons auto-derived from `desktop/icon.png` |
| `/sw.js` | pass-through service worker with a fetch handler - Chrome's installability criteria still require one in 2026 |
| page JS (via gradio `js`) | registers `/sw.js` on load |
| page head (via gradio `head`) | `apple-touch-icon`, `theme-color`, `mobile-web-app-capable` for iOS/Android chrome |

Two gradio launch flags are load-bearing for this and are documented in
`app_space.py`:

- `ssr_mode=False` - on HF the SSR node server sits in front of the Python app
  and answers `/sw.js` with its own SPA fallback, so the worker route would
  never be reached.
- `prevent_thread_lock=True` - `launch()` blocks forever by default, which
  silently skipped the route registration that follows it.

There is intentionally **no offline caching** in the worker: inference runs on
the Space's GPU, so an offline copy would be a dead UI. The worker exists to
satisfy installability and to keep the installed app a real WebAPK rather than a
bookmark shortcut.

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
