"""Bone / lung-component suppression for frontal chest radiographs.

Faithful port of the authors' reference inference script (`suppress.py`) from
`qureaiorg/bone-suppression` (Angaitkar et al., arXiv:2609.24937), wrapped in a Gradio UI.

Reference pipeline reproduced 1:1:
    full radiograph --[bone model]--> bone image        ; soft tissue   = full - bone
    soft tissue     --[lung model]--> lung component    ; non-lung soft = soft - lung

Preprocessing contract (from config.json / model card):
    resize to 1024x1024 with INTER_AREA, min-max normalise to [0, 1] per image,
    single channel, bone bright. The lung model consumes the float residual
    `soft = full - bone` exactly as computed, with NO second normalisation.
"""

import os

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import spaces  # noqa: E402  -- must precede torch / any CUDA-touching import

import time  # noqa: E402

import numpy as np  # noqa: E402
import torch  # noqa: E402
import cv2  # noqa: E402
import gradio as gr  # noqa: E402
from huggingface_hub import hf_hub_download  # noqa: E402

MODEL_ID = "qureaiorg/bone-suppression"
BONE_FILE = "weights/bone_suppression.ts"
LUNG_FILE = "weights/lung_component_suppression.ts"
SIZE = 1024

# ---------------------------------------------------------------------------
# Load the two TorchScript traces at module scope, eagerly onto the GPU.
# ---------------------------------------------------------------------------
bone_path = hf_hub_download(MODEL_ID, BONE_FILE)
lung_path = hf_hub_download(MODEL_ID, LUNG_FILE)
print(f"[startup] weights: {bone_path} | {lung_path}", flush=True)

bone_model = torch.jit.load(bone_path, map_location="cpu").eval()
lung_model = torch.jit.load(lung_path, map_location="cpu").eval()

# ZeroGPU hijacks module-scope `.to("cuda")` so the weights get packed to disk and streamed into
# VRAM on the first @spaces.GPU entry. TorchScript modules go through a C++ `.to()` path, so keep
# this guarded; `_ensure_cuda()` below re-checks the real device inside the GPU worker either way.
try:
    bone_model.to("cuda")
    lung_model.to("cuda")
    print("[startup] module-scope .to('cuda') applied to both traces", flush=True)
except Exception as exc:  # pragma: no cover - depends on the ZeroGPU runtime
    print(f"[startup] module-scope .to('cuda') not applied ({exc!r})", flush=True)


def _ensure_cuda():
    """Move both traces onto the real GPU if they are not already there.

    Runs inside the forked GPU worker (warm workers keep them resident). The device check is the
    authoritative one: the module-scope move above may or may not have been intercepted.
    """
    for model in (bone_model, lung_model):
        try:
            on_cuda = next(model.parameters()).device.type == "cuda"
        except StopIteration:
            on_cuda = True  # parameterless trace: nothing to move
        if not on_cuda:
            model.to("cuda")


# ---------------------------------------------------------------------------
# Pre / post processing (from the reference implementation)
# ---------------------------------------------------------------------------
def read_gray(path):
    """2-D float32 array at native resolution; 16-bit depth preserved when present."""
    arr = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if arr is None:
        from PIL import Image  # fallback for formats OpenCV declines

        arr = np.array(Image.open(path))
        if arr.ndim == 3:
            arr = arr[..., :3][..., ::-1]  # RGB -> BGR
    if arr is None:
        raise gr.Error("Could not read the uploaded image.")
    if arr.ndim == 3:
        if arr.shape[2] == 4:
            arr = cv2.cvtColor(arr, cv2.COLOR_BGRA2GRAY)
        else:
            arr = cv2.cvtColor(arr[..., :3], cv2.COLOR_BGR2GRAY)
    return arr.astype(np.float32)


def preprocess(arr):
    """Resize to 1024x1024 (area) and min-max normalise to [0,1]: the required convention."""
    x = cv2.resize(arr, (SIZE, SIZE), interpolation=cv2.INTER_AREA)
    lo, hi = float(x.min()), float(x.max())
    x = (x - lo) / (hi - lo + 1e-10)
    return x.astype(np.float32)


def looks_inverted(arr):
    """True when the mediastinum column is clearly DARKER than the lung fields (bone-dark input).

    The models require a clinically displayed frontal radiograph (bone bright); feeding an
    inverted image gives meaningless output. The test is scale-invariant (relative to the image's
    own dynamic range), so it works for 8- and 16-bit inputs.
    """
    h, w = arr.shape
    y0, y1 = int(0.40 * h), int(0.62 * h)
    central = arr[y0:y1, int(0.46 * w):int(0.54 * w)]
    left = arr[y0:y1, int(0.20 * w):int(0.32 * w)]
    right = arr[y0:y1, int(0.68 * w):int(0.80 * w)]
    if min(central.size, left.size, right.size) == 0:
        return False
    rng = float(arr.max() - arr.min()) + 1e-10
    ref = float((np.median(left) + np.median(right)) / 2.0)
    return (ref - float(np.median(central))) / rng > 0.04


def to_u8(x, shape=None, stretch=False):
    """Clip a [0,1]-range float image to 8 bit; optionally stretch and resize back.

    The stretch is a robust 0.5–99.5 percentile clip, not min–max: the bone and lung components
    occupy a small part of the [0,1] range, so a plain min–max would be dominated by a handful of
    bright pixels and the rib cage would be lost in amplified scatter.
    """
    y = np.asarray(x, dtype=np.float32)
    if stretch:
        lo, hi = (float(v) for v in np.percentile(y, [0.5, 99.5]))
        if hi - lo > 1e-6:
            y = (y - lo) / (hi - lo)
    y = (np.clip(y, 0.0, 1.0) * 255.0).round().astype(np.uint8)
    if shape is not None and y.shape != tuple(shape):
        y = cv2.resize(y, (shape[1], shape[0]), interpolation=cv2.INTER_CUBIC)
    return y


def first(out):
    """The traces return a tuple (predicted component, aux); take the predicted component."""
    if isinstance(out, (tuple, list)):
        out = out[0]
    if isinstance(out, dict):
        out = next(iter(out.values()))
    return out


SCALE_STRETCHED = "Contrast-stretched (for viewing)"
SCALE_RAW = "Raw [0,1] scale (as the repo's PNGs)"


@spaces.GPU(duration=15)
def decompose(
    image_path,
    output_scale=SCALE_STRETCHED,
    auto_polarity=True,
    progress=gr.Progress(),
):
    """Decompose a frontal chest radiograph into bone, lung and soft-tissue images.

    Args:
        image_path: chest radiograph (PA/AP, bone bright) — PNG/JPG/TIFF, 8- or 16-bit.
        output_scale: contrast-stretch the component images for viewing, or keep the raw scale.
        auto_polarity: invert automatically when the image looks bone-dark (inverted).
    """
    if not image_path:
        raise gr.Error("Please upload a chest radiograph first.")

    t0 = time.perf_counter()
    progress(0.05, desc="Reading image")

    _ensure_cuda()

    arr = read_gray(image_path)
    native_shape = arr.shape
    inverted = False
    if auto_polarity and looks_inverted(arr):
        arr = arr.max() - arr
        inverted = True

    x_np = preprocess(arr)  # [0,1] float32, 1024x1024
    x = torch.from_numpy(x_np)[None, None].to("cuda")

    progress(0.3, desc="Bone suppression")
    with torch.no_grad():
        full = x_np  # normalised input on the [0,1] scale
        bone = first(bone_model(x))[0, 0].float().cpu().numpy()
        soft = full - bone  # additive identity: soft_tissue = input - bone

        progress(0.65, desc="Lung-component suppression")
        xs = torch.from_numpy(soft.astype(np.float32))[None, None].to("cuda")
        lung = first(lung_model(xs))[0, 0].float().cpu().numpy()
        nonlung = soft - lung  # non-lung soft tissue = soft - lung

    progress(0.9, desc="Encoding outputs")
    stretch = output_scale == SCALE_STRETCHED
    soft_u8 = to_u8(soft, native_shape, stretch)
    bone_u8 = to_u8(bone, native_shape, stretch)
    lung_u8 = to_u8(lung, native_shape, stretch)
    nonlung_u8 = to_u8(nonlung, native_shape, stretch)

    elapsed = time.perf_counter() - t0
    h, w = native_shape
    print(f"[infer] {os.path.basename(str(image_path))} {w}x{h} inverted={inverted} "
          f"stretch={stretch} {elapsed:.2f}s", flush=True)

    status = (
        f"**Done in {elapsed:.1f}s** — output {w}×{h} · "
        f"{'contrast-stretched (0.5–99.5 pct clip)' if stretch else 'raw [0,1] scale'} · "
        f"input polarity: {'**auto-inverted** (bone-dark input detected)' if inverted else 'used as-is (bone bright)'}"
    )
    return soft_u8, bone_u8, lung_u8, nonlung_u8, status


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
CSS = """
#col-container { max-width: 1180px; margin: 0 auto; }
.dark .gradio-container { color: var(--body-text-color); }
"""

INTRO = """
# Bone & lung-component suppression for chest radiographs

Decompose a frontal (PA/AP) chest radiograph into its **bone**, **lung-component** and
**soft-tissue** images, using the suppression models of
[*Anatomy-Decomposed Chest CT Projections as Scalable Supervision for Bone Suppression in Chest
Radiographs*](https://huggingface.co/papers/2609.24937) (Angaitkar et al., 2026 — Qure.ai).

Both networks were trained **only** on synthetic supervision: per-structure projections rendered from
chest CT — no dual-energy pairs and no paired real radiographs. Each model predicts one component and
its complement is recovered by subtraction: `soft tissue = input − bone`,
`non-lung soft tissue = soft − lung`. The four panels below are exactly the decomposition the paper
reports.

Upload a **bone-bright** chest radiograph (as displayed clinically). Leave *Auto-invert* on if you are
unsure — feeding an inverted image gives meaningless output.
"""

DISCLAIMER = """
> ⚠️ **Research software — not a medical device; not for diagnostic or clinical use.**
> Trained on synthetic CT-derived projections and evaluated on adult frontal radiographs only
> (not paediatric, lateral, or portable/supine images). The lung-component output is experimental and
> has no standalone downstream validation in the paper.
>
> **Licences** — weights ([`qureaiorg/bone-suppression`](https://huggingface.co/qureaiorg/bone-suppression)):
> CC BY-NC-SA 4.0, *non-commercial research and educational use only*. Reference code: Apache-2.0.
> Example images: from the authors' own
> [`qureaiorg/ct2xr-projections`](https://huggingface.co/datasets/qureaiorg/ct2xr-projections) dataset
> (CC BY-NC-SA 4.0) — synthetic CT-derived radiographs, redistributed under the same terms.
"""

with gr.Blocks(title="Bone Suppression — Chest X-ray") as demo:
    with gr.Column(elem_id="col-container"):
        gr.Markdown(INTRO)

        with gr.Row():
            with gr.Column(scale=1):
                input_image = gr.Image(
                    type="filepath",
                    label="Chest radiograph (PA/AP, bone bright)",
                    height=430,
                    sources=["upload", "clipboard"],
                )
                run_btn = gr.Button("Decompose", variant="primary")

            with gr.Column(scale=1):
                with gr.Row():
                    out_soft = gr.Image(
                        label="Bone-suppressed radiograph (soft tissue)", height=205
                    )
                    out_bone = gr.Image(label="Predicted bone component", height=205)
                with gr.Row():
                    out_lung = gr.Image(label="Lung component (experimental)", height=205)
                    out_nonlung = gr.Image(label="Non-lung soft tissue", height=205)

        status_md = gr.Markdown()

        with gr.Accordion("Advanced settings", open=False):
            output_scale = gr.Radio(
                choices=[SCALE_STRETCHED, SCALE_RAW],
                value=SCALE_STRETCHED,
                label="Output scale",
                info=(
                    "The predictions live on the normalised input's [0,1] scale, so the raw component "
                    "images look dark (the bone image peaks near 62/255). Contrast-stretched clips "
                    "each panel to its 0.5–99.5 percentile range for display only — the paper's "
                    "decomposition figure does the same. Choose 'Raw' for the exact files the "
                    "reference script writes."
                ),
            )
            auto_polarity = gr.Checkbox(
                value=True,
                label="Auto-invert if bones appear dark",
                info="The models require a bone-bright (clinically displayed) radiograph.",
            )

        gr.Examples(
            examples=[
                ["examples/cxr_train_1_a_1.png"],
                ["examples/cxr_train_2_a_1.png"],
                ["examples/cxr_train_8_a_2.png"],
                ["examples/cxr_train_16_a_2.png"],
                ["examples/cxr_train_26_a_2.png"],
                ["examples/cxr_train_28_a_2.png"],
            ],
            inputs=[input_image],
            outputs=[out_soft, out_bone, out_lung, out_nonlung, status_md],
            fn=decompose,
            cache_examples=True,
            cache_mode="lazy",
            label="Example chest radiographs (synthetic CT-derived projections, CC BY-NC-SA 4.0)",
        )

        gr.Markdown(DISCLAIMER)

    run_btn.click(
        fn=decompose,
        inputs=[input_image, output_scale, auto_polarity],
        outputs=[out_soft, out_bone, out_lung, out_nonlung, status_md],
        api_name="decompose",
    )

if __name__ == "__main__":
    # Gradio 6 takes `theme` / `css` on launch(), not on the Blocks constructor.
    demo.launch(theme=gr.themes.Citrus(), css=CSS, mcp_server=True)
