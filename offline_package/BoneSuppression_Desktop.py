"""
BoneSuppression AI - Clinical Chest Radiograph Workstation
Native Offline Windows Desktop Application
Based on Qure.ai CT2XR Research (arXiv:2609.24937)

Supports:
- 100% Offline execution on air-gapped clinical systems
- CUDA GPU acceleration and CPU multi-threading
- DICOM (.dcm), PNG, JPG, TIFF image input
- Interactive split curtain slider & 4-panel decomposition
- Batch folder processing
"""

import os
import sys
import time
import math
import numpy as np
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageOps

# Check PyTorch availability
try:
    import torch
except ImportError:
    torch = None

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import pydicom
except ImportError:
    pydicom = None

HERE = os.path.dirname(os.path.abspath(__file__))
WEIGHTS_DIR = os.path.join(HERE, "weights")
BONE_WEIGHTS_PATH = os.path.join(WEIGHTS_DIR, "bone_suppression.ts")
LUNG_WEIGHTS_PATH = os.path.join(WEIGHTS_DIR, "lung_component_suppression.ts")
SIZE = 1024


class BoneSuppressionApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BoneSuppression AI - Chest X-Ray Studio (Windows Offline)")
        self.geometry("1280x850")
        self.minsize(1024, 700)
        self.configure(bg="#0f172a")

        self.current_image_path = None
        self.original_np = None
        self.soft_np = None
        self.bone_np = None
        self.lung_np = None
        self.nonlung_np = None

        self.bone_model = None
        self.lung_model = None
        self.device = "cuda" if (torch and torch.cuda.is_available()) else "cpu"

        self.view_mode = tk.StringVar(value="split")
        self.stretch_var = tk.BooleanVar(value=True)
        self.auto_invert_var = tk.BooleanVar(value=True)
        self.slider_pos = tk.DoubleVar(value=0.5)

        self.init_ui()
        self.check_models()

    def check_models(self):
        has_bone = os.path.exists(BONE_WEIGHTS_PATH)
        has_lung = os.path.exists(LUNG_WEIGHTS_PATH)

        if not has_bone or not has_lung:
            msg = (
                "فایل‌های وزن مدل در پوشه weights یافت نشدند!\n\n"
                "برای استفاده کاملاً آفلاین، لطفاً اسکریپت download_all_weights.bat را اجرا کنید\n"
                "یا فایل‌های زیر را در پوشه weights قرار دهید:\n"
                "- bone_suppression.ts (417 MB)\n"
                "- lung_component_suppression.ts (417 MB)\n\n"
                "Weights not found! Run 'download_all_weights.bat' first."
            )
            self.status_label.config(text="⚠ هشدار: وزن‌های مدل در پوشه weights یافت نشدند", fg="#f59e0b")
        else:
            size_mb = (os.path.getsize(BONE_WEIGHTS_PATH) + os.path.getsize(LUNG_WEIGHTS_PATH)) / (1024 * 1024)
            self.status_label.config(
                text=f"✓ مدل‌ها آماده هستند ({size_mb:.1f} MB) | سخت‌افزار: {self.device.upper()}",
                fg="#10b981"
            )

    def load_models_eagerly(self):
        if self.bone_model is not None:
            return True
        if not torch:
            messagebox.showerror("Error", "PyTorch is not installed in this environment.")
            return False
        if not os.path.exists(BONE_WEIGHTS_PATH):
            messagebox.showerror("Weights Missing", "Please run download_all_weights.bat first to fetch the model weights.")
            return False

        try:
            self.status_label.config(text="در حال بارگذاری مدل‌ها در حافظه...", fg="#38bdf8")
            self.update_idletasks()
            dev = torch.device(self.device)
            self.bone_model = torch.jit.load(BONE_WEIGHTS_PATH, map_location=dev).eval()
            if os.path.exists(LUNG_WEIGHTS_PATH):
                self.lung_model = torch.jit.load(LUNG_WEIGHTS_PATH, map_location=dev).eval()
            self.status_label.config(text=f"✓ مدل‌ها در حافظه بارگذاری شدند ({self.device.upper()})", fg="#10b981")
            return True
        except Exception as e:
            messagebox.showerror("Model Load Error", str(e))
            self.status_label.config(text=f"خطا در بارگذاری مدل: {e}", fg="#ef4444")
            return False

    def init_ui(self):
        # Top toolbar
        toolbar = tk.Frame(self, bg="#1e293b", height=50)
        toolbar.pack(fill=tk.X, side=tk.TOP, padx=0, pady=0)

        title = tk.Label(toolbar, text="🫁 BoneSuppression AI", font=("Segoe UI", 12, "bold"), fg="#f8fafc", bg="#1e293b")
        title.pack(side=tk.LEFT, padx=16, pady=10)

        btn_open = tk.Button(toolbar, text="📂 باز کردن تصویر / DICOM", command=self.open_image, bg="#2563eb", fg="white",
                             font=("Segoe UI", 9, "bold"), padx=12, pady=4, relief=tk.FLAT)
        btn_open.pack(side=tk.LEFT, padx=8)

        btn_batch = tk.Button(toolbar, text="📁 پردازش گروهی پوشه", command=self.batch_process, bg="#334155", fg="white",
                              font=("Segoe UI", 9), padx=10, pady=4, relief=tk.FLAT)
        btn_batch.pack(side=tk.LEFT, padx=4)

        btn_run = tk.Button(toolbar, text="⚡ اجرای جداسازی استخوان", command=self.run_inference, bg="#059669", fg="white",
                            font=("Segoe UI", 9, "bold"), padx=14, pady=4, relief=tk.FLAT)
        btn_run.pack(side=tk.LEFT, padx=8)

        btn_save = tk.Button(toolbar, text="💾 ذخیره نتایج", command=self.save_results, bg="#334155", fg="white",
                             font=("Segoe UI", 9), padx=10, pady=4, relief=tk.FLAT)
        btn_save.pack(side=tk.LEFT, padx=4)

        # Device selector
        dev_frame = tk.Frame(toolbar, bg="#1e293b")
        dev_frame.pack(side=tk.RIGHT, padx=16)
        tk.Label(dev_frame, text="Device:", fg="#94a3b8", bg="#1e293b", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=4)
        self.dev_combo = ttk.Combobox(dev_frame, values=["cuda", "cpu"], width=6, state="readonly")
        self.dev_combo.set(self.device)
        self.dev_combo.pack(side=tk.LEFT)
        self.dev_combo.bind("<<ComboboxSelected>>", self.on_device_change)

        # Main viewport
        self.canvas_frame = tk.Frame(self, bg="#0b0f17")
        self.canvas_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        self.canvas = tk.Canvas(self.canvas_frame, bg="#000000", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<B1-Motion>", self.on_slider_drag)
        self.canvas.bind("<Configure>", self.on_resize)

        # Bottom control bar
        bottom_bar = tk.Frame(self, bg="#1e293b", height=45)
        bottom_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=0, pady=0)

        # View modes
        tk.Radiobutton(bottom_bar, text="اسلایدر مقایسه‌ای (Curtain)", variable=self.view_mode, value="split",
                       command=self.render_view, bg="#1e293b", fg="#e2e8f0", selectcolor="#0f172a").pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(bottom_bar, text="کنار هم (Side-by-Side)", variable=self.view_mode, value="dual",
                       command=self.render_view, bg="#1e293b", fg="#e2e8f0", selectcolor="#0f172a").pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(bottom_bar, text="۴ پنل همزمان (Quad)", variable=self.view_mode, value="quad",
                       command=self.render_view, bg="#1e293b", fg="#e2e8f0", selectcolor="#0f172a").pack(side=tk.LEFT, padx=10)

        # Settings
        tk.Checkbutton(bottom_bar, text="بهبود کنتراست (0.5-99.5%)", variable=self.stretch_var, command=self.render_view,
                       bg="#1e293b", fg="#e2e8f0", selectcolor="#0f172a").pack(side=tk.LEFT, padx=10)
        tk.Checkbutton(bottom_bar, text="تشخیص خودکار جهت قطبیت (Auto Invert)", variable=self.auto_invert_var,
                       bg="#1e293b", fg="#e2e8f0", selectcolor="#0f172a").pack(side=tk.LEFT, padx=10)

        # Status Label
        self.status_label = tk.Label(bottom_bar, text="آماده به کار", font=("Segoe UI", 9), fg="#94a3b8", bg="#1e293b")
        self.status_label.pack(side=tk.RIGHT, padx=16)

    def on_device_change(self, event=None):
        self.device = self.dev_combo.get()
        self.bone_model = None
        self.lung_model = None
        self.status_label.config(text=f"سخت‌افزار پردازش تغییر یافت: {self.device.upper()}", fg="#38bdf8")

    def open_image(self):
        filetypes = [
            ("All Supported Formats", "*.png;*.jpg;*.jpeg;*.tif;*.tiff;*.dcm;*.bmp"),
            ("DICOM Medical Files", "*.dcm"),
            ("PNG / JPEG Images", "*.png;*.jpg;*.jpeg"),
            ("All Files", "*.*")
        ]
        path = filedialog.askopenfilename(title="Select Chest Radiograph", filetypes=filetypes)
        if not path:
            return

        self.current_image_path = path
        try:
            arr = self.read_image(path)
            self.original_np = arr
            self.soft_np = None
            self.bone_np = None
            self.lung_np = None
            self.nonlung_np = None
            self.status_label.config(text=f"فایل باز شد: {os.path.basename(path)} ({arr.shape[1]}x{arr.shape[0]})", fg="#e2e8f0")
            self.render_view()
        except Exception as e:
            messagebox.showerror("Error Reading File", str(e))

    def read_image(self, path):
        if path.lower().endswith(".dcm"):
            if not pydicom:
                raise RuntimeError("pydicom is required to read .dcm files.")
            ds = pydicom.dcmread(path)
            arr = ds.pixel_array.astype(np.float32)
            if getattr(ds, "PhotometricInterpretation", "") == "MONOCHROME1":
                arr = arr.max() - arr
            lo, hi = arr.min(), arr.max()
            arr = (arr - lo) / (hi - lo + 1e-10)
            return arr

        if cv2:
            arr = cv2.imread(path, cv2.IMREAD_UNCHANGED)
            if arr is not None:
                if arr.ndim == 3:
                    arr = cv2.cvtColor(arr[..., :3], cv2.COLOR_BGR2GRAY)
                arr = arr.astype(np.float32)
                lo, hi = arr.min(), arr.max()
                arr = (arr - lo) / (hi - lo + 1e-10)
                return arr

        # Fallback to PIL
        pil_img = Image.open(path).convert("L")
        arr = np.array(pil_img, dtype=np.float32) / 255.0
        return arr

    def looks_inverted(self, arr):
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

    def run_inference(self):
        if self.original_np is None:
            messagebox.showinfo("اطلاعیه", "لطفاً ابتدا یک تصویر رادیوگرافی قفسه سینه را باز کنید.")
            return

        if not self.load_models_eagerly():
            return

        t0 = time.time()
        self.status_label.config(text="در حال اجرای شبکه عصبی روی مدل استخوان...", fg="#38bdf8")
        self.update_idletasks()

        arr = self.original_np.copy()
        if self.auto_invert_var.get() and self.looks_inverted(arr):
            arr = arr.max() - arr

        # Preprocess: 1024x1024 area resize
        if cv2:
            x_np = cv2.resize(arr, (SIZE, SIZE), interpolation=cv2.INTER_AREA)
        else:
            pil_temp = Image.fromarray((arr * 255).astype(np.uint8)).resize((SIZE, SIZE), Image.Resampling.BOX)
            x_np = np.array(pil_temp, dtype=np.float32) / 255.0

        lo, hi = float(x_np.min()), float(x_np.max())
        x_np = (x_np - lo) / (hi - lo + 1e-10)

        dev = torch.device(self.device)
        x = torch.from_numpy(x_np.astype(np.float32))[None, None].to(dev)

        with torch.no_grad():
            bone_out = self.bone_model(x)
            if isinstance(bone_out, (tuple, list)):
                bone_out = bone_out[0]
            bone = bone_out[0, 0].float().cpu().numpy()
            soft = x_np - bone

            if self.lung_model:
                xs = torch.from_numpy(soft.astype(np.float32))[None, None].to(dev)
                lung_out = self.lung_model(xs)
                if isinstance(lung_out, (tuple, list)):
                    lung_out = lung_out[0]
                lung = lung_out[0, 0].float().cpu().numpy()
                nonlung = soft - lung
            else:
                lung = np.zeros_like(soft)
                nonlung = soft

        # Resize back to native shape
        h, w = arr.shape
        if cv2:
            self.soft_np = cv2.resize(soft, (w, h), interpolation=cv2.INTER_CUBIC)
            self.bone_np = cv2.resize(bone, (w, h), interpolation=cv2.INTER_CUBIC)
            self.lung_np = cv2.resize(lung, (w, h), interpolation=cv2.INTER_CUBIC)
            self.nonlung_np = cv2.resize(nonlung, (w, h), interpolation=cv2.INTER_CUBIC)
        else:
            self.soft_np = np.array(Image.fromarray(soft).resize((w, h), Image.Resampling.BICUBIC))
            self.bone_np = np.array(Image.fromarray(bone).resize((w, h), Image.Resampling.BICUBIC))
            self.lung_np = np.array(Image.fromarray(lung).resize((w, h), Image.Resampling.BICUBIC))
            self.nonlung_np = np.array(Image.fromarray(nonlung).resize((w, h), Image.Resampling.BICUBIC))

        elapsed = time.time() - t0
        self.status_label.config(text=f"✓ جداسازی با موفقیت در {elapsed:.2f} ثانیه انجام شد", fg="#10b981")
        self.render_view()

    def to_display_image(self, arr):
        y = arr.copy()
        if self.stretch_var.get():
            lo, hi = np.percentile(y, [0.5, 99.5])
            if hi - lo > 1e-6:
                y = (y - lo) / (hi - lo)
        u8 = (np.clip(y, 0.0, 1.0) * 255.0).astype(np.uint8)
        return Image.fromarray(u8)

    def on_slider_drag(self, event):
        cw = self.canvas.winfo_width()
        if cw > 0:
            self.slider_pos.set(max(0.0, min(1.0, event.x / cw)))
            self.render_view()

    def on_resize(self, event=None):
        self.render_view()

    def render_view(self):
        if self.original_np is None:
            self.canvas.delete("all")
            cw = self.canvas.winfo_width()
            ch = self.canvas.winfo_height()
            self.canvas.create_text(
                cw // 2, ch // 2,
                text="تصویر رادیوگرافی قفسه سینه را از منوی بالا باز کنید\nClick 'باز کردن تصویر' to open a Chest X-Ray",
                fill="#64748b", font=("Segoe UI", 14), justify=tk.CENTER
            )
            return

        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw <= 10 or ch <= 10:
            return

        mode = self.view_mode.get()
        orig_img = self.to_display_image(self.original_np)
        soft_img = self.to_display_image(self.soft_np) if self.soft_np is not None else orig_img

        if mode == "split":
            # Resize both to canvas size maintaining aspect ratio
            img_w, img_h = orig_img.size
            scale = min((cw - 20) / img_w, (ch - 20) / img_h)
            nw, nh = int(img_w * scale), int(img_h * scale)
            ox, oy = (cw - nw) // 2, (ch - nh) // 2

            r_orig = orig_img.resize((nw, nh), Image.Resampling.BILINEAR)
            r_soft = soft_img.resize((nw, nh), Image.Resampling.BILINEAR)

            split_x = int(nw * self.slider_pos.get())
            composite = Image.new("RGB", (nw, nh))
            composite.paste(r_orig.crop((0, 0, split_x, nh)), (0, 0))
            composite.paste(r_soft.crop((split_x, 0, nw, nh)), (split_x, 0))

            self.tk_img = ImageTk.PhotoImage(composite)
            self.canvas.delete("all")
            self.canvas.create_image(ox, oy, anchor=tk.NW, image=self.tk_img)

            # Draw divider line
            line_x = ox + split_x
            self.canvas.create_line(line_x, oy, line_x, oy + nh, fill="#38bdf8", width=2)
            self.canvas.create_oval(line_x - 8, oy + nh // 2 - 8, line_x + 8, oy + nh // 2 + 8, fill="#38bdf8", outline="white")

            self.canvas.create_text(ox + 20, oy + 20, text="تصویر اصلی (Original)", fill="white", anchor=tk.NW, font=("Segoe UI", 10, "bold"))
            self.canvas.create_text(ox + nw - 20, oy + 20, text="حذف استخوان (Soft Tissue)", fill="#38bdf8", anchor=tk.NE, font=("Segoe UI", 10, "bold"))

        elif mode == "dual":
            # Side by side
            half_w = (cw - 30) // 2
            img_w, img_h = orig_img.size
            scale = min(half_w / img_w, (ch - 20) / img_h)
            nw, nh = int(img_w * scale), int(img_h * scale)
            oy = (ch - nh) // 2

            r_orig = orig_img.resize((nw, nh), Image.Resampling.BILINEAR)
            r_soft = soft_img.resize((nw, nh), Image.Resampling.BILINEAR)

            self.tk_orig = ImageTk.PhotoImage(r_orig)
            self.tk_soft = ImageTk.PhotoImage(r_soft)

            self.canvas.delete("all")
            self.canvas.create_image(10, oy, anchor=tk.NW, image=self.tk_orig)
            self.canvas.create_image(20 + nw, oy, anchor=tk.NW, image=self.tk_soft)

            self.canvas.create_text(20, oy + 10, text="تصویر کامل (Full Radiograph)", fill="white", anchor=tk.NW, font=("Segoe UI", 10, "bold"))
            self.canvas.create_text(30 + nw, oy + 10, text="بافت نرم - حذف استخوان (Soft Tissue)", fill="#38bdf8", anchor=tk.NW, font=("Segoe UI", 10, "bold"))

        elif mode == "quad":
            # 4 panels: Original, Bone, Soft Tissue, Lung Component
            panel_w = (cw - 30) // 2
            panel_h = (ch - 30) // 2
            img_w, img_h = orig_img.size
            scale = min(panel_w / img_w, panel_h / img_h)
            nw, nh = int(img_w * scale), int(img_h * scale)

            bone_img = self.to_display_image(self.bone_np) if self.bone_np is not None else Image.new("L", (img_w, img_h))
            lung_img = self.to_display_image(self.lung_np) if self.lung_np is not None else Image.new("L", (img_w, img_h))

            self.tk_p1 = ImageTk.PhotoImage(orig_img.resize((nw, nh), Image.Resampling.BILINEAR))
            self.tk_p2 = ImageTk.PhotoImage(bone_img.resize((nw, nh), Image.Resampling.BILINEAR))
            self.tk_p3 = ImageTk.PhotoImage(soft_img.resize((nw, nh), Image.Resampling.BILINEAR))
            self.tk_p4 = ImageTk.PhotoImage(lung_img.resize((nw, nh), Image.Resampling.BILINEAR))

            self.canvas.delete("all")
            self.canvas.create_image(10, 10, anchor=tk.NW, image=self.tk_p1)
            self.canvas.create_image(20 + nw, 10, anchor=tk.NW, image=self.tk_p2)
            self.canvas.create_image(10, 20 + nh, anchor=tk.NW, image=self.tk_p3)
            self.canvas.create_image(20 + nw, 20 + nh, anchor=tk.NW, image=self.tk_p4)

            self.canvas.create_text(20, 20, text="Full Radiograph", fill="white", anchor=tk.NW)
            self.canvas.create_text(30 + nw, 20, text="Predicted Bone", fill="#f59e0b", anchor=tk.NW)
            self.canvas.create_text(20, 30 + nh, text="Bone-Suppressed (Soft)", fill="#10b981", anchor=tk.NW)
            self.canvas.create_text(30 + nw, 30 + nh, text="Lung Component", fill="#38bdf8", anchor=tk.NW)

    def save_results(self):
        if self.soft_np is None:
            messagebox.showinfo("اطلاعیه", "ابتدا جداسازی استخوان را اجرا کنید.")
            return

        dir_path = filedialog.askdirectory(title="پوشه ذخیره خروجی‌ها را انتخاب کنید")
        if not dir_path:
            return

        stem = os.path.splitext(os.path.basename(self.current_image_path))[0] if self.current_image_path else "cxr"
        self.to_display_image(self.soft_np).save(os.path.join(dir_path, f"{stem}_soft_tissue.png"))
        self.to_display_image(self.bone_np).save(os.path.join(dir_path, f"{stem}_bone.png"))
        if self.lung_np is not None:
            self.to_display_image(self.lung_np).save(os.path.join(dir_path, f"{stem}_lung_component.png"))
        messagebox.showinfo("موفقیت", f"تصاویر در مسیر زیر ذخیره شدند:\n{dir_path}")

    def batch_process(self):
        in_dir = filedialog.askdirectory(title="پوشه تصاویر ورودی (DICOM/PNG/JPG) را انتخاب کنید")
        if not in_dir:
            return
        out_dir = filedialog.askdirectory(title="پوشه خروجی را انتخاب کنید")
        if not out_dir:
            return

        if not self.load_models_eagerly():
            return

        files = [os.path.join(in_dir, f) for f in os.listdir(in_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.dcm', '.tif'))]
        if not files:
            messagebox.showinfo("یافت نشد", "هیچ تصویر سازگاری در پوشه ورودی یافت نشد.")
            return

        count = 0
        for p in files:
            try:
                stem = os.path.splitext(os.path.basename(p))[0]
                arr = self.read_image(p)
                if self.auto_invert_var.get() and self.looks_inverted(arr):
                    arr = arr.max() - arr
                x_np = cv2.resize(arr, (SIZE, SIZE), interpolation=cv2.INTER_AREA) if cv2 else arr
                lo, hi = float(x_np.min()), float(x_np.max())
                x_np = (x_np - lo) / (hi - lo + 1e-10)

                dev = torch.device(self.device)
                x = torch.from_numpy(x_np.astype(np.float32))[None, None].to(dev)
                with torch.no_grad():
                    bone_out = self.bone_model(x)
                    if isinstance(bone_out, (tuple, list)):
                        bone_out = bone_out[0]
                    bone = bone_out[0, 0].float().cpu().numpy()
                    soft = x_np - bone

                h, w = arr.shape
                s_u8 = ((np.clip(soft, 0, 1)) * 255).astype(np.uint8)
                b_u8 = ((np.clip(bone, 0, 1)) * 255).astype(np.uint8)

                if cv2:
                    s_u8 = cv2.resize(s_u8, (w, h))
                    b_u8 = cv2.resize(b_u8, (w, h))
                    cv2.imwrite(os.path.join(out_dir, f"{stem}_soft.png"), s_u8)
                    cv2.imwrite(os.path.join(out_dir, f"{stem}_bone.png"), b_u8)
                else:
                    Image.fromarray(s_u8).resize((w, h)).save(os.path.join(out_dir, f"{stem}_soft.png"))
                    Image.fromarray(b_u8).resize((w, h)).save(os.path.join(out_dir, f"{stem}_bone.png"))
                count += 1
            except Exception as e:
                print(f"Error processing {p}: {e}")

        messagebox.showinfo("پایان پردازش گروهی", f"تعداد {count} تصویر با موفقیت پردازش و ذخیره شد.")


if __name__ == "__main__":
    app = BoneSuppressionApp()
    app.mainloop()
