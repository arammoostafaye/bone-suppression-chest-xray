#!/usr/bin/env python3
"""Bone suppression (and optional lung-component suppression) for frontal chest radiographs.
Reference CLI script from Qure.ai (arXiv:2609.24937)
"""
import argparse, glob, os, sys
import numpy as np
import torch
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
BONE_FILE = os.path.join(HERE, "weights", "bone_suppression.ts")
LUNG_FILE = os.path.join(HERE, "weights", "lung_component_suppression.ts")
SIZE = 1024
EXTS = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".dcm")

def read_gray(path):
    if path.lower().endswith(".dcm"):
        import pydicom
        ds = pydicom.dcmread(path)
        arr = ds.pixel_array.astype(np.float32)
        if getattr(ds, "PhotometricInterpretation", "") == "MONOCHROME1":
            arr = arr.max() - arr
        return arr
    arr = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if arr is None:
        raise RuntimeError(f"cannot read {path}")
    if arr.ndim == 3:
        arr = cv2.cvtColor(arr[..., :3], cv2.COLOR_BGR2GRAY)
    return arr.astype(np.float32)

def preprocess(arr):
    x = cv2.resize(arr, (SIZE, SIZE), interpolation=cv2.INTER_AREA)
    lo, hi = float(x.min()), float(x.max())
    x = (x - lo) / (hi - lo + 1e-10)
    return torch.from_numpy(x.astype(np.float32))[None, None]

def to_u8(x, shape=None):
    y = (np.clip(x, 0.0, 1.0) * 255.0).round().astype(np.uint8)
    if shape is not None and y.shape != tuple(shape):
        y = cv2.resize(y, (shape[1], shape[0]), interpolation=cv2.INTER_CUBIC)
    return y

def first(out):
    if isinstance(out, (tuple, list)):
        return out[0]
    if isinstance(out, dict):
        return next(iter(out.values()))
    return out

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True, help="image file or directory")
    ap.add_argument("--output", required=True, help="output directory")
    ap.add_argument("--lung", action="store_true", help="also run lung-component suppression")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--bone_weights", default=BONE_WEIGHTS_PATH if 'BONE_WEIGHTS_PATH' in globals() else BONE_FILE)
    ap.add_argument("--lung_weights", default=LUNG_WEIGHTS_PATH if 'LUNG_WEIGHTS_PATH' in globals() else LUNG_FILE)
    a = ap.parse_args()

    paths = sorted(p for p in (glob.glob(os.path.join(a.input, "*")) if os.path.isdir(a.input) else [a.input]) if p.lower().endswith(EXTS))
    if not paths:
        sys.exit(f"no images found under {a.input}")

    os.makedirs(a.output, exist_ok=True)
    dev = torch.device(a.device)
    print(f"Loading bone model: {a.bone_weights} on {dev}")
    bone_m = torch.jit.load(a.bone_weights, map_location=dev).eval()
    lung_m = None
    if a.lung and os.path.exists(a.lung_weights):
        print(f"Loading lung model: {a.lung_weights} on {dev}")
        lung_m = torch.jit.load(a.lung_weights, map_location=dev).eval()

    with torch.no_grad():
        for p in paths:
            stem = os.path.splitext(os.path.basename(p))[0]
            arr = read_gray(p)
            shape = arr.shape
            x = preprocess(arr).to(dev)
            full = x[0, 0].cpu().numpy()
            bone = first(bone_m(x))[0, 0].float().cpu().numpy()
            soft = full - bone
            cv2.imwrite(os.path.join(a.output, f"{stem}_bone.png"), to_u8(bone, shape))
            cv2.imwrite(os.path.join(a.output, f"{stem}_soft_tissue.png"), to_u8(soft, shape))
            print(f"Processed {stem}: bone, soft_tissue")
            if lung_m:
                xs = torch.from_numpy(soft.astype(np.float32))[None, None].to(dev)
                lung = first(lung_m(xs))[0, 0].float().cpu().numpy()
                nonlung = soft - lung
                cv2.imwrite(os.path.join(a.output, f"{stem}_lung_component.png"), to_u8(lung, shape))
                cv2.imwrite(os.path.join(a.output, f"{stem}_nonlung_soft_tissue.png"), to_u8(nonlung, shape))

if __name__ == "__main__":
    main()
