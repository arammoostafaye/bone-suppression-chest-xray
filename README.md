---
title: Bone Suppression Chest X-ray
emoji: 🫁
colorFrom: red
colorTo: green
sdk: gradio
sdk_version: 6.28.0
app_file: app.py
python_version: "3.12"
short_description: Decompose a chest X-ray into bone and soft-tissue images
startup_duration_timeout: 30m
---

# Bone & lung-component suppression for chest radiographs

Gradio demo for the suppression models of

> *Anatomy-Decomposed Chest Computed Tomography (CT) Projections as Scalable Supervision for Bone
> Suppression in Chest Radiographs* — Angaitkar, Kumar, Satia, Rao, Mittal, Tadepalli, Putha
> ([arXiv:2609.24937](https://arxiv.org/abs/2609.24937), 2026; Qure.ai).

Weights: [`qureaiorg/bone-suppression`](https://huggingface.co/qureaiorg/bone-suppression) —
two TorchScript traces, loaded and run **verbatim** as in the authors' reference script
(`suppress.py`); the preprocessing contract (1024×1024 area resize, per-image min–max normalisation
to `[0,1]`, single channel, bone bright) is reproduced exactly.

## What it does

A frontal (PA/AP) chest radiograph is decomposed into four images by applying the two models in
sequence, as the paper does:

```
full radiograph --[bone model]--> bone image        ; soft tissue   = full − bone
soft tissue     --[lung model]--> lung component    ; non-lung soft = soft − lung
```

Each model predicts one component; the complement is recovered by subtraction. The lung model
consumes the floating-point residual `soft = full − bone` **exactly as computed, with no second
normalisation** — that is the trained inference pipeline.

## Notes on the outputs

The predictions live on the normalised input's `[0,1]` scale, so the raw component images look dark
(in the authors' example the bone image peaks near 62/255). By default the panels are
**contrast-stretched** (each clipped to its 0.5–99.5 percentile range) for viewing — the paper's
decomposition figure does the same. Switch *Output scale* to *Raw* to get the exact files the
reference script writes.

The models require a **bone-bright** radiograph, as displayed clinically; feeding an inverted image
gives meaningless output. *Auto-invert if bones appear dark* detects and corrects this (a
scale-invariant comparison of the mediastinum against the lung fields).

## Limitations

Trained on **synthetic** supervision only (per-structure projections rendered from chest CT); no
dual-energy pairs and no paired real radiographs. Evaluated on adult frontal radiographs from public
datasets (TBX11K, Node21, VinDr-CXR, JSRT) — not evaluated on paediatric, lateral, or portable/supine
images. The lung-component output is an experimental model-derived estimate of vessels and other
intrapulmonary structure, with no standalone downstream validation in the paper.

**This is research software, not a medical device, and is not for diagnostic or clinical use.**

## Licences

- Weights (`weights/*.ts`) — CC BY-NC-SA 4.0, **non-commercial research and educational use only**
  (see `weights/LICENSE-WEIGHTS.txt` in the model repo).
- Reference code (`suppress.py`, `config.json`) — Apache-2.0.
- Example radiographs in `examples/` — from the authors' own
  [`qureaiorg/ct2xr-projections`](https://huggingface.co/datasets/qureaiorg/ct2xr-projections)
  dataset (CC BY-NC-SA 4.0). They are synthetic CT-derived projections of CT-RATE volumes,
  redistributed here under the same share-alike terms with attribution to Qure.ai.

## Hardware

ZeroGPU (`zero-a10g`), single `@spaces.GPU(duration=...)` call covering both models.
