# Running the UI in GitHub Codespaces

`app.py` is the untouched mirror of the Hugging Face Space: it hard-codes CUDA and relies on the
ZeroGPU runtime, so it only runs on HF. This directory documents how to get the **same graphical
interface** running in a GitHub Codespace instead.

Two files were added for that, and nothing else was changed:

| File | Purpose |
|---|---|
| `app_codespaces.py` | `app.py` with the device chosen at runtime (`cuda` if present, else `cpu`) and the server bound to `0.0.0.0`. Generated from `app.py`; see the diff below. |
| `.devcontainer/devcontainer.json` | Python 3.12 image, installs the CPU wheel of torch, pre-downloads the weights, forwards port 7860. |
| `.devcontainer/requirements-codespaces.txt` | gradio 6.28.0 + the runtime deps that HF preinstalls on the Space. |

`app.py`, `README.md`, `requirements.txt`, `.gitattributes` and `examples/` stay byte-identical to
the upstream Space.

## Quick start

1. Open the repo → **Code** → **Codespaces** → **Create codespace on main**.
2. Wait for `postCreateCommand` to finish (installs torch CPU + gradio, a few minutes).
3. In the terminal:
   ```bash
   python app_codespaces.py
   ```
4. The **PORTS** panel forwards `7860` automatically and opens the UI in a browser tab.
   If it does not, click *Forward a Port* → `7860`.

The weights (~800 MB) are fetched from `qureaiorg/bone-suppression` on first start and then cached
in `~/.cache/huggingface`. `postStartCommand` warms that cache when the codespace boots.

## Hardware reality

Personal GitHub accounts get **CPU-only** Codespaces machines — there is no GPU option, so this runs
the real pipeline on CPU. It works, it is just slower than the Space's A10G.

Measured footprint of the two TorchScript traces:

```
bone  params=  96.10M  weights=0.384 GB fp32
lung  params=  96.10M  weights=0.384 GB fp32
```

Both models resident cost ~1.4 GB of RAM **before** any activation, and each forward pass runs at
1024×1024 in fp32. `.devcontainer/devcontainer.json` therefore requests **4 CPUs / 16 GB**:

```json
"hostRequirements": { "cpus": 4, "memory": "16gb" }
```

If a run is killed by the OOM killer (exit code 137), raise that to `"cpus": 8, "memory": "32gb"`,
then **Codespaces → ... → Rebuild container** — changing machine type needs a rebuild.

### Quota and cost

A 4-core codespace burns the free personal allowance (120 core-hours/month) four times as fast as a
2-core one: roughly **30 hours/month** free. Past that it bills at $0.18/core-hour. Two habits keep
the bill at zero:

- Stop the codespace when done (the button in the VS Code status bar, or `Codespaces → Stop`).
- **Delete** codespaces you are finished with — stopped ones still charge $0.07/GB-month for the disk.

## Diff between `app.py` and `app_codespaces.py`

Regenerate or review it any time with:

```bash
diff app.py app_codespaces.py
```

The only functional changes are:

1. `DEVICE = "cuda" if torch.cuda.is_available() else "cpu"`, replacing every hard-coded `"cuda"`.
2. `_ensure_cuda()` → `_ensure_device()`, checking against `DEVICE`.
3. `demo.launch(..., server_name="0.0.0.0", server_port=$PORT|7860)` so Codespaces can forward it.

The inference maths, the preprocessing contract (1024×1024 `INTER_AREA` resize, per-image min–max
normalisation, bone-bright polarity, no second normalisation on the `soft = full − bone` residual),
the UI layout and the output scaling are all untouched. On the HF Space `app.py` still uses CUDA via
`@spaces.GPU` exactly as upstream.

## If `app.py` upstream changes

Re-derive the variant rather than editing it by hand, so the two cannot drift apart silently:

```bash
diff app.py app_codespaces.py > /tmp/cpu.patch   # inspect what the variant adds
# then update app.py from the Space and re-apply the three changes listed above
```

## Licence reminder

Unchanged from `README.md`: the weights are **CC BY-NC-SA 4.0**, non-commercial research and
educational use only. This is research software, not a medical device.
