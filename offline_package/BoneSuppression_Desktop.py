"""
BoneSuppression AI - Clinical Chest Radiograph Workstation
Native Offline Windows Desktop Application
Based on Qure.ai CT2XR Research (arXiv:2609.24937)

Developer / توسعه و آماده‌سازی نسخه دسکتاپ ویندوز:
آرام مصطفائی (Aram Mostafaei)
پرسنل واحد امور تصویربرداری بیمارستان بوعلی - شبکه بهداشت و درمان مریوان

Supports:
- 100% Offline execution on air-gapped clinical systems
- User authentication & access control (boalimri.ir / aram)
- Hierarchical animated clinical splash screen
- Modern Shadcn/GPUI-inspired dark medical interface
- Multi-tab developer profile & attribution center
- Automatic detection and reuse of existing model weights
"""

import os
import sys
import time
import json
import hashlib
import traceback
import numpy as np
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk

# Safe import PyTorch
try:
    import torch
except ImportError:
    torch = None

# Safe import OpenCV
try:
    import cv2
except ImportError:
    cv2 = None

# Safe import pydicom
try:
    import pydicom
except ImportError:
    pydicom = None

# -----------------------------------------------------------------------------
# Path Resolution & Model Weight Re-use (Never re-download if already exists)
# -----------------------------------------------------------------------------
if getattr(sys, 'frozen', False):
    EXE_DIR = os.path.dirname(os.path.abspath(sys.executable))
    BUNDLE_DIR = getattr(sys, '_MEIPASS', EXE_DIR)
else:
    EXE_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = EXE_DIR

PARENT_DIR = os.path.dirname(EXE_DIR)

SEARCH_DIRS = [
    EXE_DIR,
    BUNDLE_DIR,
    os.path.join(EXE_DIR, "weights"),
    os.path.join(BUNDLE_DIR, "weights"),
    os.path.join(EXE_DIR, "_internal"),
    os.path.join(EXE_DIR, "_internal", "weights"),
    os.path.join(BUNDLE_DIR, "_internal"),
    os.path.join(BUNDLE_DIR, "_internal", "weights"),
    # Also look in sibling folders from older installations (e.g. BoneSuppressionAI)
    PARENT_DIR,
    os.path.join(PARENT_DIR, "weights"),
    os.path.join(PARENT_DIR, "BoneSuppressionAI", "weights"),
    os.path.join(PARENT_DIR, "BoneSuppressionAI", "_internal", "weights"),
    os.getcwd()
]

def find_file(rel_path):
    """Finds a file across multiple candidate directories, prioritizing existing weights."""
    for base in SEARCH_DIRS:
        if not base:
            continue
        candidate = os.path.join(base, rel_path)
        if os.path.isfile(candidate):
            return candidate
    return os.path.join(BUNDLE_DIR, rel_path)

CONFIG_PATH = find_file("config.json")
BONE_WEIGHTS_PATH = find_file(os.path.join("weights", "bone_suppression.ts"))
LUNG_WEIGHTS_PATH = find_file(os.path.join("weights", "lung_component_suppression.ts"))
SIZE = 1024

# Default credentials
DEFAULT_USER = "boalimri.ir"
DEFAULT_PASS = "aram"
DEFAULT_PASS_HASH = "912863a494a953280178cd8812895062696e4493e3c764f9e58c49bfaa6cca20"

# Application Metadata & Developer Profile
APP_TITLE = "BoneSuppression AI - Chest X-Ray Studio"
HOSPITAL_TITLE = "بیمارستان بوعلی مریوان"
NETWORK_TITLE = "شبکه بهداشت و درمان مریوان"
DEVELOPER_NAME = "آرام مصطفائی"
DEVELOPER_ROLE = "پرسنل واحد امور تصویربرداری بیمارستان بوعلی"
DEVELOPER_PHONES = ["09356808002", "09188766949"]
DEVELOPER_EMAIL = "arammoostafaye@gmail.com"
DEVELOPER_GITHUB = "https://github.com/arammoostafaye"
UPSTREAM_SOURCE = "https://huggingface.co/qureaiorg/bone-suppression"

# -----------------------------------------------------------------------------
# Modern Dark UI Theme Tokens (Inspired by GPUI / Shadcn / Tailwind Slate)
# -----------------------------------------------------------------------------
C_CANVAS      = "#090d16"   # Deepest background
C_CARD        = "#111827"   # Elevated card background
C_CARD_HOVER  = "#172236"   # Card hover highlight
C_HEADER      = "#0f172a"   # Navigation header
C_TOOLBAR     = "#182234"   # Primary action toolbar
C_BORDER      = "#27354a"   # Subtle clean borders
C_BORDER_SUBTLE="#1e293b"   # Very subtle dividers
C_TEXT_LIGHT  = "#f8fafc"   # Primary text
C_TEXT_MUTED  = "#94a3b8"   # Secondary text
C_TEXT_DIM    = "#64748b"   # Tertiary hints
C_CYAN        = "#38bdf8"   # Primary brand accent
C_BLUE        = "#2563eb"   # Primary action button
C_BLUE_HOVER  = "#3b82f6"
C_GREEN       = "#059669"   # Inference / success button
C_GREEN_HOVER = "#10b981"
C_SLATE       = "#334155"   # Neutral button
C_SLATE_HOVER = "#475569"
C_AMBER       = "#f59e0b"   # Warning / accent
C_RED         = "#dc2626"   # Danger / exit
C_RED_HOVER   = "#ef4444"


def create_modern_button(parent, text, command, bg, hover_bg, fg="white",
                         font=("Segoe UI", 9, "bold"), padx=14, pady=6, relief=tk.FLAT, bd=0):
    """Creates a modern flat button with responsive hover highlight."""
    btn = tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                    activebackground=hover_bg, activeforeground=fg,
                    font=font, padx=padx, pady=pady, relief=relief, bd=bd,
                    cursor="hand2", highlightthickness=0)
    btn.bind("<Enter>", lambda e: btn.configure(bg=hover_bg))
    btn.bind("<Leave>", lambda e: btn.configure(bg=bg))
    return btn


# -----------------------------------------------------------------------------
# Modern 3-Tab About & Attribution Modal (Replacing the plain text box)
# -----------------------------------------------------------------------------
class ModernAboutDialog(tk.Toplevel):
    """Redesigned, multi-tab clinical and developer presentation center."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("درباره نرم‌افزار Bone Suppression Chest X-ray")
        self.geometry("860x720")
        self.minsize(780, 620)
        self.configure(bg=C_CANVAS)

        # Center on parent or screen
        self.update_idletasks()
        w, h = 860, 720
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.transient(parent)
        self.bind("<Escape>", lambda e: self.destroy())

        self.current_tab = "overview"
        self.init_ui()
        self.lift()
        self.focus_force()

    def init_ui(self):
        # Top Header Bar
        top_bar = tk.Frame(self, bg=C_HEADER, bd=1, relief=tk.SOLID, highlightbackground=C_BORDER, highlightthickness=1)
        top_bar.pack(fill=tk.X, padx=16, pady=(16, 10))

        h_content = tk.Frame(top_bar, bg=C_HEADER)
        h_content.pack(fill=tk.X, padx=16, pady=12)

        tk.Label(h_content, text="🫁 درباره نرم‌افزار Bone Suppression Chest X-ray",
                 font=("Segoe UI", 13, "bold"), fg=C_CYAN, bg=C_HEADER).pack(side=tk.RIGHT)
        tk.Label(h_content, text=f"{HOSPITAL_TITLE} - {NETWORK_TITLE} | {DEVELOPER_ROLE}",
                 font=("Segoe UI", 9), fg=C_TEXT_MUTED, bg=C_HEADER).pack(side=tk.LEFT)

        # Segmented Tabs Bar (GPUI / Shadcn Pill Style)
        tab_bar = tk.Frame(self, bg=C_CANVAS)
        tab_bar.pack(fill=tk.X, padx=16, pady=(0, 10))

        self.btn_tab_overview = create_modern_button(
            tab_bar, "📖 معرفی و یادداشت توسعه‌دهنده",
            lambda: self.switch_tab("overview"),
            bg=C_BLUE, hover_bg=C_BLUE_HOVER, font=("Segoe UI", 9, "bold"), padx=16, pady=6
        )
        self.btn_tab_overview.pack(side=tk.RIGHT, padx=4)

        self.btn_tab_developer = create_modern_button(
            tab_bar, "👨‍💻 مشخصات سازنده و ارتباط",
            lambda: self.switch_tab("developer"),
            bg=C_SLATE, hover_bg=C_SLATE_HOVER, font=("Segoe UI", 9), padx=16, pady=6
        )
        self.btn_tab_developer.pack(side=tk.RIGHT, padx=4)

        self.btn_tab_legal = create_modern_button(
            tab_bar, "⚖️ حقوق مالکیت و سلب مسئولیت بالینی",
            lambda: self.switch_tab("legal"),
            bg=C_SLATE, hover_bg=C_SLATE_HOVER, font=("Segoe UI", 9), padx=16, pady=6
        )
        self.btn_tab_legal.pack(side=tk.RIGHT, padx=4)

        # Tab Content Container
        self.content_frame = tk.Frame(self, bg=C_CANVAS)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=0)

        # Bottom Action Bar
        bottom_bar = tk.Frame(self, bg=C_CANVAS)
        bottom_bar.pack(fill=tk.X, padx=16, pady=12)

        btn_close = create_modern_button(bottom_bar, "بستن پنجره (Close / Esc)", self.destroy,
                                         bg=C_SLATE, hover_bg=C_SLATE_HOVER, font=("Segoe UI", 9, "bold"), padx=22, pady=6)
        btn_close.pack(side=tk.RIGHT)

        # Render initial tab
        self.render_overview_tab()

    def switch_tab(self, tab_id):
        self.current_tab = tab_id
        for w in self.content_frame.winfo_children():
            w.destroy()

        # Update tab button styles
        self.btn_tab_overview.config(bg=C_BLUE if tab_id == "overview" else C_SLATE)
        self.btn_tab_developer.config(bg=C_BLUE if tab_id == "developer" else C_SLATE)
        self.btn_tab_legal.config(bg=C_BLUE if tab_id == "legal" else C_SLATE)

        if tab_id == "overview":
            self.render_overview_tab()
        elif tab_id == "developer":
            self.render_developer_tab()
        elif tab_id == "legal":
            self.render_legal_tab()

    def render_overview_tab(self):
        """Tab 1: Beautiful scrollable cards presenting the developer statement."""
        canvas = tk.Canvas(self.content_frame, bg=C_CANVAS, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.content_frame, orient=tk.VERTICAL, command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=C_CANVAS)

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        cw = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(cw, width=e.width - 20))
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Card 1: Project Mission
        card1 = tk.Frame(scroll_frame, bg=C_CARD, bd=1, relief=tk.SOLID, highlightbackground=C_BORDER, highlightthickness=1)
        card1.pack(fill=tk.X, pady=(0, 10))

        tk.Label(card1, text="🫁 معرفی نرم‌افزار Bone Suppression Chest X-ray", font=("Segoe UI", 11, "bold"),
                 fg=C_CYAN, bg=C_CARD, anchor=tk.E).pack(fill=tk.X, padx=18, pady=(14, 6))

        tk.Label(card1, text=(
            "این نرم‌افزار با هدف پردازش تصاویر رادیوگرافی قفسه سینه (Chest X-ray) و جداسازی اثر سایه‌های "
            "استخوانی از تصویر، با بهره‌گیری از روش‌های پردازش تصویر و هوش مصنوعی توسعه داده شده است."
        ), font=("Segoe UI", 10), fg=C_TEXT_LIGHT, bg=C_CARD, justify=tk.RIGHT, wraplength=760).pack(fill=tk.X, padx=18, pady=(0, 14))

        # Card 2: Developer Personal Note
        card2 = tk.Frame(scroll_frame, bg=C_CARD, bd=1, relief=tk.SOLID, highlightbackground=C_BORDER, highlightthickness=1)
        card2.pack(fill=tk.X, pady=(0, 10))

        tk.Label(card2, text="✍️ یادداشت توسعه‌دهنده", font=("Segoe UI", 11, "bold"),
                 fg="#10b981", bg=C_CARD, anchor=tk.E).pack(fill=tk.X, padx=18, pady=(14, 6))

        p1 = (
            "اینجانب آرام مصطفائی، به‌عنوان عضوی کوچک از مجموعه نظام سلامت شهرستان مریوان و از پرسنل واحد "
            "امور تصویربرداری بیمارستان بوعلی، همواره علاقه‌مند به استفاده از فناوری‌های نوین در جهت بهبود "
            "فرایندهای کاری و ارتقای امکانات حوزه تصویربرداری پزشکی بوده‌ام."
        )
        tk.Label(card2, text=p1, font=("Segoe UI", 10), fg=C_TEXT_LIGHT, bg=C_CARD,
                 justify=tk.RIGHT, wraplength=760).pack(fill=tk.X, padx=18, pady=(0, 8))

        p2 = (
            "این پروژه حاصل علاقه شخصی به برنامه‌نویسی، فناوری و هوش مصنوعی و تلاشی در راستای پیوند دانش فناوری "
            "اطلاعات با تجربه عملی در محیط درمانی است. امید دارم این گام کوچک بتواند زمینه‌ای برای یادگیری، "
            "توسعه ایده‌های نوآورانه و کمک به پیشرفت ابزارهای مرتبط با تصویربرداری پزشکی فراهم کند."
        )
        tk.Label(card2, text=p2, font=("Segoe UI", 10), fg=C_TEXT_LIGHT, bg=C_CARD,
                 justify=tk.RIGHT, wraplength=760).pack(fill=tk.X, padx=18, pady=(0, 8))

        p3 = (
            "باور دارم که پیشرفت نظام سلامت، علاوه بر تلاش‌های ارزشمند کادر درمان، می‌تواند از ایده‌های خلاقانه، "
            "یادگیری مستمر و به‌کارگیری مسئولانه فناوری نیز بهره‌مند شود."
        )
        tk.Label(card2, text=p3, font=("Segoe UI", 10), fg=C_TEXT_LIGHT, bg=C_CARD,
                 justify=tk.RIGHT, wraplength=760).pack(fill=tk.X, padx=18, pady=(0, 8))

        p4 = "این نرم‌افزار را با افتخار و به‌عنوان تلاشی شخصی، در راستای خدمت به جامعه درمانی و همشهریان عزیزم در شهرستان مریوان ارائه می‌کنم."
        tk.Label(card2, text=p4, font=("Segoe UI", 10, "bold"), fg=C_CYAN, bg=C_CARD,
                 justify=tk.RIGHT, wraplength=760).pack(fill=tk.X, padx=18, pady=(0, 14))

        # Card 3: Gratitude
        card3 = tk.Frame(scroll_frame, bg=C_CARD, bd=1, relief=tk.SOLID, highlightbackground=C_BORDER, highlightthickness=1)
        card3.pack(fill=tk.X)
        tk.Label(card3, text="با سپاس از تمامی افرادی که در مسیر یادگیری، توسعه و پیشرفت علم و فناوری تلاش می‌کنند.",
                 font=("Segoe UI", 9, "italic"), fg=C_TEXT_MUTED, bg=C_CARD, justify=tk.CENTER).pack(padx=18, pady=12)

    def render_developer_tab(self):
        """Tab 2: Sleek developer profile cards with direct contact details."""
        container = tk.Frame(self.content_frame, bg=C_CANVAS)
        container.pack(fill=tk.BOTH, expand=True)

        # Profile Hero Card
        hero = tk.Frame(container, bg=C_CARD, bd=1, relief=tk.SOLID, highlightbackground=C_BORDER, highlightthickness=1)
        hero.pack(fill=tk.X, pady=(0, 14))

        top_hero = tk.Frame(hero, bg=C_CARD)
        top_hero.pack(fill=tk.X, padx=20, pady=18)

        tk.Label(top_hero, text="👨‍⚕️", font=("Segoe UI", 38), bg=C_CARD).pack(side=tk.RIGHT, padx=(16, 0))

        info_box = tk.Frame(top_hero, bg=C_CARD)
        info_box.pack(side=tk.RIGHT, fill=tk.X, expand=True)

        tk.Label(info_box, text=DEVELOPER_NAME, font=("Segoe UI", 16, "bold"), fg=C_TEXT_LIGHT, bg=C_CARD, anchor=tk.E).pack(fill=tk.X)
        tk.Label(info_box, text=DEVELOPER_ROLE, font=("Segoe UI", 11), fg=C_CYAN, bg=C_CARD, anchor=tk.E).pack(fill=tk.X, pady=(2, 2))
        tk.Label(info_box, text=NETWORK_TITLE, font=("Segoe UI", 10), fg=C_TEXT_MUTED, bg=C_CARD, anchor=tk.E).pack(fill=tk.X)

        # Contact Details Grid
        grid_frame = tk.Frame(container, bg=C_CANVAS)
        grid_frame.pack(fill=tk.BOTH, expand=True)

        contacts = [
            ("📱 شماره تماس همراه (همراه اول):", DEVELOPER_PHONES[1], "#10b981"),
            ("📞 شماره تماس همراه (ایرانسل):", DEVELOPER_PHONES[0], "#38bdf8"),
            ("✉️ آدرس رایانامه (Email):", DEVELOPER_EMAIL, "#818cf8"),
            ("🌐 صفحه گیت‌هاب (GitHub):", DEVELOPER_GITHUB, "#f59e0b"),
        ]

        for i, (title, val, color) in enumerate(contacts):
            row = i // 2
            col = i % 2
            c_box = tk.Frame(grid_frame, bg=C_CARD, bd=1, relief=tk.SOLID, highlightbackground=C_BORDER, highlightthickness=1)
            c_box.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)
            grid_frame.grid_columnconfigure(col, weight=1)
            grid_frame.grid_rowconfigure(row, weight=1)

            tk.Label(c_box, text=title, font=("Segoe UI", 9, "bold"), fg=C_TEXT_MUTED, bg=C_CARD, anchor=tk.E).pack(fill=tk.X, padx=14, pady=(14, 4))
            tk.Label(c_box, text=val, font=("Segoe UI", 11, "bold"), fg=color, bg=C_CARD, anchor=tk.E).pack(fill=tk.X, padx=14, pady=(0, 10))

            btn_copy = create_modern_button(
                c_box, "کپی در حافظه",
                lambda v=val: self.copy_to_clipboard(v),
                bg=C_SLATE, hover_bg=C_SLATE_HOVER, font=("Segoe UI", 8), padx=10, pady=3
            )
            btn_copy.pack(side=tk.LEFT, padx=14, pady=(0, 12))

    def copy_to_clipboard(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("کپی شد", f"متن با موفقیت کپی شد:\n{text}")

    def render_legal_tab(self):
        """Tab 3: Clinical disclaimer and upstream attribution."""
        container = tk.Frame(self.content_frame, bg=C_CANVAS)
        container.pack(fill=tk.BOTH, expand=True)

        # Clinical Disclaimer Warning Card
        alert_card = tk.Frame(container, bg="#1c1917", bd=1, relief=tk.SOLID, highlightbackground=C_AMBER, highlightthickness=1)
        alert_card.pack(fill=tk.X, pady=(0, 14))

        tk.Label(alert_card, text="⚠ بیانیه بالینی و سلب مسئولیت پزشکی", font=("Segoe UI", 11, "bold"),
                 fg=C_AMBER, bg="#1c1917", anchor=tk.E).pack(fill=tk.X, padx=18, pady=(14, 6))

        tk.Label(alert_card, text=(
            "این نرم‌افزار یک ابزار پردازش تصویر است و خروجی آن به‌تنهایی جایگزین بررسی تصاویر اصلی، "
            "تفسیر پزشک رادیولوژیست یا تصمیم‌گیری بالینی نیست."
        ), font=("Segoe UI", 10, "bold"), fg="#fef3c7", bg="#1c1917", justify=tk.RIGHT, wraplength=760).pack(fill=tk.X, padx=18, pady=(0, 14))

        # Upstream Attribution Card
        attr_card = tk.Frame(container, bg=C_CARD, bd=1, relief=tk.SOLID, highlightbackground=C_BORDER, highlightthickness=1)
        attr_card.pack(fill=tk.BOTH, expand=True)

        tk.Label(attr_card, text="🏛️ منبع اصلی پروژه و حقوق مالکیت", font=("Segoe UI", 11, "bold"),
                 fg=C_CYAN, bg=C_CARD, anchor=tk.E).pack(fill=tk.X, padx=18, pady=(14, 6))

        t1 = (
            "این نرم‌افزار بر پایه پروژه اصلی Bone Suppression ارائه‌شده توسط مجموعه Qure.ai توسعه یافته است.\n\n"
            f"منبع اصلی پروژه و مدل:\n{UPSTREAM_SOURCE}\n\n"
            "با احترام به حقوق مالکیت فکری پدیدآورندگان اصلی، کلیه حقوق مربوط به کد، مدل و اجزای متعلق به "
            "پروژه اصلی تابع مجوز و شرایط اعلام‌شده توسط صاحبان آن است.\n\n"
            "نقش اینجانب، آرام مصطفائی، توسعه و آماده‌سازی نرم‌افزار برای اجرا در سیستم‌عامل ویندوز و "
            "فراهم‌کردن امکان استفاده از آن در قالب یک برنامه دسکتاپ بوده است.\n\n"
            "این نسخه با هدف تسهیل اجرای نرم‌افزار در محیط ویندوز تهیه شده و به‌عنوان نسخه‌ای مستقل از نظر "
            "بسته‌بندی و اجرا ارائه می‌شود؛ این موضوع به‌معنای مالکیت اینجانب بر مدل یا کد اصلی پروژه نیست.\n\n"
            "از مجموعه Qure.ai و تمامی افرادی که در توسعه و انتشار این پروژه مشارکت داشته‌اند، قدردانی می‌کنم."
        )
        tk.Label(attr_card, text=t1, font=("Segoe UI", 9), fg=C_TEXT_LIGHT, bg=C_CARD,
                 justify=tk.RIGHT, wraplength=760).pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 14))


# -----------------------------------------------------------------------------
# Main Application Class
# -----------------------------------------------------------------------------
class BoneSuppressionApp(tk.Tk):
    """BoneSuppression AI Desktop Workstation with animated splash, modern UI, and hospital branding."""
    def __init__(self):
        super().__init__()
        self.title("BoneSuppression AI - Chest X-Ray Studio | بیمارستان بوعلی مریوان")
        self.geometry("1280x850")
        self.minsize(1050, 720)
        self.configure(bg=C_CANVAS)

        # Center main window on launch
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(0, (sw - 1280) // 2)
        y = max(0, (sh - 850) // 2)
        self.geometry(f"1280x850+{x}+{y}")

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

        # Container hierarchy
        self.splash_container = tk.Frame(self, bg=C_CANVAS)
        self.login_container = tk.Frame(self, bg=C_CANVAS)
        self.main_container = tk.Frame(self, bg=C_CANVAS)

        self.init_splash_ui()
        self.init_login_ui()
        self.init_workstation_ui()

        # Start with animated splash
        self.show_splash()

    # -------------------------------------------------------------------------
    # 1. Animated Hierarchical Splash Screen
    # -------------------------------------------------------------------------
    def init_splash_ui(self):
        """Constructs the elegant hierarchical tree splash container."""
        center_box = tk.Frame(self.splash_container, bg=C_CANVAS)
        center_box.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        card = tk.Frame(center_box, bg=C_CARD, bd=1, relief=tk.SOLID,
                        highlightbackground=C_BORDER, highlightthickness=1, padx=44, pady=36)
        card.pack()

        # Medical Pulse Logo
        tk.Label(card, text="🫁", font=("Segoe UI", 42), bg=C_CARD, fg=C_CYAN).pack(pady=(0, 4))
        tk.Label(card, text="BoneSuppression AI", font=("Segoe UI", 16, "bold"), fg=C_TEXT_LIGHT, bg=C_CARD).pack()
        tk.Label(card, text="سامانه هوشمند تفکیک استخوان در رادیوگرافی قفسه سینه", font=("Segoe UI", 9), fg=C_TEXT_MUTED, bg=C_CARD).pack(pady=(2, 14))

        # Thin divider
        tk.Frame(card, bg=C_BORDER_SUBTLE, height=1, width=420).pack(pady=4)

        # Tree Container (Nodes will appear sequentially)
        self.tree_frame = tk.Frame(card, bg=C_CARD, width=420)
        self.tree_frame.pack(fill=tk.X, pady=16)

        # Node 1: Health Network
        self.node1 = tk.Frame(self.tree_frame, bg=C_CARD)
        tk.Label(self.node1, text="🏛️", font=("Segoe UI", 12), bg=C_CARD).pack(side=tk.RIGHT, padx=(6, 0))
        tk.Label(self.node1, text="شبکه بهداشت و درمان مریوان", font=("Segoe UI", 12, "bold"), fg=C_CYAN, bg=C_CARD).pack(side=tk.RIGHT)

        # Node 2: Hospital (Indented Branch)
        self.node2 = tk.Frame(self.tree_frame, bg=C_CARD)
        tk.Label(self.node2, text="└── 🏥 بیمارستان بوعلی", font=("Segoe UI", 11, "bold"), fg="#10b981", bg=C_CARD).pack(side=tk.RIGHT, padx=(0, 24))

        # Node 3: Imaging Unit (Indented Branch)
        self.node3 = tk.Frame(self.tree_frame, bg=C_CARD)
        tk.Label(self.node3, text="└── 🩻 واحد امور تصویربرداری", font=("Segoe UI", 10, "bold"), fg="#38bdf8", bg=C_CARD).pack(side=tk.RIGHT, padx=(0, 48))

        # Node 4: Developer (Indented Branch)
        self.node4 = tk.Frame(self.tree_frame, bg=C_CARD)
        tk.Label(self.node4, text="└── 👨‍💻 آرام مصطفائی", font=("Segoe UI", 10, "bold"), fg=C_AMBER, bg=C_CARD).pack(side=tk.RIGHT, padx=(0, 72))

        # Progress indicator
        self.splash_status = tk.Label(card, text="آماده‌سازی ماژول‌های پردازش هوش مصنوعی...", font=("Segoe UI", 8), fg=C_TEXT_DIM, bg=C_CARD)
        self.splash_status.pack(pady=(12, 10))

        # Direct Continue / Skip Button
        btn_skip = create_modern_button(card, "ورود مستقیم (Skip ➔)", self.end_splash,
                                        bg=C_SLATE, hover_bg=C_SLATE_HOVER, font=("Segoe UI", 8), padx=16, pady=4)
        btn_skip.pack()

    def show_splash(self):
        self.main_container.pack_forget()
        self.login_container.pack_forget()
        self.splash_container.pack(fill=tk.BOTH, expand=True)

        # Key shortcut to skip anytime
        self.bind("<Return>", lambda e: self.end_splash())
        self.bind("<space>", lambda e: self.end_splash())

        # Staggered animation sequence
        self.after(300, lambda: self.node1.pack(fill=tk.X, pady=3))
        self.after(850, lambda: self.node2.pack(fill=tk.X, pady=3))
        self.after(1400, lambda: self.node3.pack(fill=tk.X, pady=3))
        self.after(1950, lambda: self.node4.pack(fill=tk.X, pady=3))
        self.after(2500, lambda: self.splash_status.config(text="● هسته هوش مصنوعی آماده اتصال است", fg="#10b981"))
        self.after(3100, self.end_splash)

    def end_splash(self):
        self.unbind("<Return>")
        self.unbind("<space>")
        self.splash_container.pack_forget()
        self.show_login_view()

    # -------------------------------------------------------------------------
    # 2. Modern Clinical Login Card
    # -------------------------------------------------------------------------
    def init_login_ui(self):
        """Constructs the sleek login screen inside login_container."""
        center_box = tk.Frame(self.login_container, bg=C_CANVAS)
        center_box.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        card = tk.Frame(center_box, bg=C_CARD, bd=1, relief=tk.SOLID,
                        highlightbackground=C_BORDER, highlightthickness=1, padx=36, pady=28)
        card.pack()

        tk.Label(card, text="🏥", font=("Segoe UI", 34), bg=C_CARD, fg=C_CYAN).pack(pady=(4, 2))
        tk.Label(card, text=HOSPITAL_TITLE, font=("Segoe UI", 13, "bold"), fg=C_TEXT_LIGHT, bg=C_CARD).pack()
        tk.Label(card, text=f"{NETWORK_TITLE} - {DEVELOPER_ROLE}", font=("Segoe UI", 9), fg=C_TEXT_MUTED, bg=C_CARD).pack(pady=(2, 10))

        tk.Frame(card, bg=C_BORDER_SUBTLE, height=1, width=380).pack(pady=4)

        tk.Label(card, text="🫁 BoneSuppression AI - ورود به سامانه", font=("Segoe UI", 12, "bold"), fg=C_CYAN, bg=C_CARD).pack(pady=(8, 2))
        tk.Label(card, text="جهت دسترسی به محیط استودیو، مشخصات ورود را درج فرمایید", font=("Segoe UI", 8), fg=C_TEXT_MUTED, bg=C_CARD).pack(pady=(0, 16))

        form = tk.Frame(card, bg=C_CARD, width=360)
        form.pack(fill=tk.X)

        tk.Label(form, text="نام کاربری (Username):", font=("Segoe UI", 9, "bold"), fg=C_TEXT_LIGHT, bg=C_CARD, anchor=tk.E).pack(fill=tk.X, pady=(4, 2))
        self.entry_user = tk.Entry(form, font=("Segoe UI", 10), bg="#0b0f19", fg="white",
                                   insertbackground="white", bd=1, relief=tk.SOLID, highlightthickness=1, highlightbackground=C_BORDER)
        self.entry_user.pack(fill=tk.X, ipady=6, pady=(0, 10))
        self.entry_user.insert(0, DEFAULT_USER)

        tk.Label(form, text="رمز عبور (Password):", font=("Segoe UI", 9, "bold"), fg=C_TEXT_LIGHT, bg=C_CARD, anchor=tk.E).pack(fill=tk.X, pady=(4, 2))
        self.entry_pass = tk.Entry(form, font=("Segoe UI", 10), show="•", bg="#0b0f19", fg="white",
                                   insertbackground="white", bd=1, relief=tk.SOLID, highlightthickness=1, highlightbackground=C_BORDER)
        self.entry_pass.pack(fill=tk.X, ipady=6, pady=(0, 6))

        self.err_label = tk.Label(form, text="", font=("Segoe UI", 9, "bold"), fg=C_RED_HOVER, bg=C_CARD)
        self.err_label.pack(fill=tk.X, pady=(2, 6))

        btn_box = tk.Frame(card, bg=C_CARD)
        btn_box.pack(fill=tk.X, pady=(6, 12))

        btn_login = create_modern_button(btn_box, "✓ ورود به سامانه", self.on_login_attempt,
                                         bg=C_GREEN, hover_bg=C_GREEN_HOVER, font=("Segoe UI", 10, "bold"), pady=8)
        btn_login.pack(fill=tk.X, pady=(0, 8))

        self.entry_user.bind("<Return>", self.on_login_attempt)
        self.entry_pass.bind("<Return>", self.on_login_attempt)

        footer = tk.Frame(card, bg=C_CARD)
        footer.pack(fill=tk.X, pady=(8, 0))
        tk.Label(footer, text=f"توسعه و آماده‌سازی دسکتاپ: {DEVELOPER_NAME}", font=("Segoe UI", 8), fg=C_TEXT_DIM, bg=C_CARD).pack()

    def show_login_view(self):
        self.splash_container.pack_forget()
        self.main_container.pack_forget()
        self.login_container.pack(fill=tk.BOTH, expand=True)
        self.entry_pass.delete(0, tk.END)
        self.err_label.config(text="")
        self.entry_user.focus_set()

    def check_credentials(self, username, password):
        u = username.strip().lower()
        p = password.strip()
        if u == DEFAULT_USER.lower() and (p == DEFAULT_PASS or hashlib.sha256(p.encode()).hexdigest() == DEFAULT_PASS_HASH):
            return True

        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                auth = cfg.get("auth", {})
                cfg_u = auth.get("username", "").strip().lower()
                cfg_p = auth.get("initial_password_plain", "")
                cfg_h = auth.get("password_hash", "")
                if cfg_u and u == cfg_u:
                    if p == cfg_p or hashlib.sha256(p.encode()).hexdigest() == cfg_h:
                        return True
            except Exception:
                pass
        return False

    def on_login_attempt(self, event=None):
        u = self.entry_user.get()
        p = self.entry_pass.get()
        if self.check_credentials(u, p):
            self.show_workstation_view()
        else:
            self.err_label.config(text="❌ نام کاربری یا رمز عبور اشتباه است!")
            self.entry_pass.delete(0, tk.END)
            self.entry_pass.focus_set()

    def on_logout(self):
        if messagebox.askyesno("خروج از سامانه", "آیا می‌خواهید از سامانه خارج شوید؟"):
            self.show_login_view()

    def show_workstation_view(self):
        self.splash_container.pack_forget()
        self.login_container.pack_forget()
        self.main_container.pack(fill=tk.BOTH, expand=True)
        self.check_models()
        self.render_view()

    # -------------------------------------------------------------------------
    # 3. Workstation UI & Radiograph Processing
    # -------------------------------------------------------------------------
    def init_workstation_ui(self):
        # Header Bar
        header_bar = tk.Frame(self.main_container, bg=C_HEADER, height=44, bd=0)
        header_bar.pack(fill=tk.X, side=tk.TOP)

        brand_frame = tk.Frame(header_bar, bg=C_HEADER)
        brand_frame.pack(side=tk.LEFT, padx=14, pady=6)

        tk.Label(brand_frame, text="🫁 BoneSuppression AI", font=("Segoe UI", 12, "bold"), fg=C_CYAN, bg=C_HEADER).pack(side=tk.LEFT)
        tk.Label(brand_frame, text=" | ", font=("Segoe UI", 11), fg=C_BORDER, bg=C_HEADER).pack(side=tk.LEFT)
        tk.Label(brand_frame, text=f"{HOSPITAL_TITLE} - {DEVELOPER_NAME}", font=("Segoe UI", 9), fg=C_TEXT_MUTED, bg=C_HEADER).pack(side=tk.LEFT)

        right_header = tk.Frame(header_bar, bg=C_HEADER)
        right_header.pack(side=tk.RIGHT, padx=12, pady=6)

        tk.Label(right_header, text="👤 boalimri.ir", font=("Segoe UI", 9, "bold"), fg="#10b981", bg="#0b0f19",
                 padx=8, pady=3, bd=1, relief=tk.SOLID, highlightbackground=C_BORDER, highlightthickness=1).pack(side=tk.LEFT, padx=6)

        btn_about = create_modern_button(right_header, "ℹ️ درباره نرم‌افزار", self.open_about,
                                         bg=C_BLUE, hover_bg=C_BLUE_HOVER, font=("Segoe UI", 8, "bold"), padx=10, pady=3)
        btn_about.pack(side=tk.LEFT, padx=4)

        btn_logout = create_modern_button(right_header, "🔒 خروج", self.on_logout,
                                          bg=C_SLATE, hover_bg=C_RED, font=("Segoe UI", 8), padx=8, pady=3)
        btn_logout.pack(side=tk.LEFT, padx=4)

        tk.Frame(self.main_container, bg=C_BORDER, height=1).pack(fill=tk.X, side=tk.TOP)

        # Toolbar
        toolbar = tk.Frame(self.main_container, bg=C_TOOLBAR, height=48)
        toolbar.pack(fill=tk.X, side=tk.TOP, padx=0, pady=0)

        btn_open = create_modern_button(toolbar, "📂 باز کردن تصویر / DICOM", self.open_image,
                                        bg=C_BLUE, hover_bg=C_BLUE_HOVER, font=("Segoe UI", 9, "bold"), padx=14, pady=6)
        btn_open.pack(side=tk.LEFT, padx=(14, 6), pady=8)

        btn_run = create_modern_button(toolbar, "⚡ اجرای جداسازی استخوان", self.run_inference,
                                       bg=C_GREEN, hover_bg=C_GREEN_HOVER, font=("Segoe UI", 9, "bold"), padx=16, pady=6)
        btn_run.pack(side=tk.LEFT, padx=6, pady=8)

        btn_batch = create_modern_button(toolbar, "📁 پردازش گروهی پوشه", self.batch_process,
                                         bg=C_SLATE, hover_bg=C_SLATE_HOVER, font=("Segoe UI", 9), padx=12, pady=6)
        btn_batch.pack(side=tk.LEFT, padx=6, pady=8)

        btn_save = create_modern_button(toolbar, "💾 ذخیره نتایج", self.save_results,
                                        bg=C_SLATE, hover_bg=C_SLATE_HOVER, font=("Segoe UI", 9), padx=12, pady=6)
        btn_save.pack(side=tk.LEFT, padx=6, pady=8)

        dev_frame = tk.Frame(toolbar, bg=C_TOOLBAR)
        dev_frame.pack(side=tk.RIGHT, padx=14, pady=8)

        tk.Label(dev_frame, text="سخت‌افزار پردازش:", fg=C_TEXT_MUTED, bg=C_TOOLBAR, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=6)
        self.dev_combo = ttk.Combobox(dev_frame, values=["cuda", "cpu"], width=7, state="readonly", font=("Segoe UI", 9))
        self.dev_combo.set(self.device)
        self.dev_combo.pack(side=tk.LEFT)
        self.dev_combo.bind("<<ComboboxSelected>>", self.on_device_change)

        # Viewport Canvas
        self.canvas_frame = tk.Frame(self.main_container, bg=C_CANVAS, bd=0)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(8, 4))

        self.canvas = tk.Canvas(self.canvas_frame, bg="#000000", highlightthickness=1, highlightbackground=C_BORDER)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<B1-Motion>", self.on_slider_drag)
        self.canvas.bind("<Button-1>", self.on_slider_click)
        self.canvas.bind("<Configure>", self.on_resize)

        # Bottom Bar
        bottom_bar = tk.Frame(self.main_container, bg=C_HEADER, height=44, bd=1, relief=tk.SOLID,
                              highlightbackground=C_BORDER, highlightthickness=1)
        bottom_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=0, pady=0)

        modes_box = tk.Frame(bottom_bar, bg=C_HEADER)
        modes_box.pack(side=tk.LEFT, padx=10, pady=6)

        tk.Radiobutton(modes_box, text="اسلایدر مقایسه‌ای (Curtain)", variable=self.view_mode, value="split",
                       command=self.render_view, bg=C_HEADER, fg=C_TEXT_LIGHT, selectcolor=C_CANVAS,
                       activebackground=C_HEADER, activeforeground=C_CYAN, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=8)

        tk.Radiobutton(modes_box, text="کنار هم (Side-by-Side)", variable=self.view_mode, value="dual",
                       command=self.render_view, bg=C_HEADER, fg=C_TEXT_LIGHT, selectcolor=C_CANVAS,
                       activebackground=C_HEADER, activeforeground=C_CYAN, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=8)

        tk.Radiobutton(modes_box, text="۴ پنل همزمان (Quad)", variable=self.view_mode, value="quad",
                       command=self.render_view, bg=C_HEADER, fg=C_TEXT_LIGHT, selectcolor=C_CANVAS,
                       activebackground=C_HEADER, activeforeground=C_CYAN, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=8)

        settings_box = tk.Frame(bottom_bar, bg=C_HEADER)
        settings_box.pack(side=tk.LEFT, padx=12, pady=6)

        tk.Checkbutton(settings_box, text="بهبود کنتراست (0.5-99.5%)", variable=self.stretch_var, command=self.render_view,
                       bg=C_HEADER, fg=C_TEXT_LIGHT, selectcolor=C_CANVAS,
                       activebackground=C_HEADER, activeforeground=C_CYAN, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=8)

        tk.Checkbutton(settings_box, text="تشخیص خودکار جهت قطبیت (Auto Invert)", variable=self.auto_invert_var,
                       bg=C_HEADER, fg=C_TEXT_LIGHT, selectcolor=C_CANVAS,
                       activebackground=C_HEADER, activeforeground=C_CYAN, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=8)

        self.status_label = tk.Label(bottom_bar, text="آماده به کار", font=("Segoe UI", 9), fg=C_TEXT_MUTED, bg=C_HEADER)
        self.status_label.pack(side=tk.RIGHT, padx=16, pady=6)

    def open_about(self):
        ModernAboutDialog(self)

    def check_models(self):
        has_bone = os.path.exists(BONE_WEIGHTS_PATH)
        has_lung = os.path.exists(LUNG_WEIGHTS_PATH)

        if not has_bone or not has_lung:
            self.status_label.config(text="⚠ فایل مدل در پوشه weights یافت نشد", fg=C_AMBER)
        else:
            size_mb = (os.path.getsize(BONE_WEIGHTS_PATH) + os.path.getsize(LUNG_WEIGHTS_PATH)) / (1024 * 1024)
            self.status_label.config(
                text=f"● مدل‌ها آماده هستند ({size_mb:.1f} MB) | سخت‌افزار: {self.device.upper()}",
                fg="#10b981"
            )

    def load_models_eagerly(self):
        if self.bone_model is not None:
            return True
        if not torch:
            messagebox.showerror("خطا", "کتابخانه PyTorch بارگذاری نشده است.")
            return False
        if not os.path.exists(BONE_WEIGHTS_PATH):
            messagebox.showerror("فایل مدل یافت نشد", f"فایل مدل هوش مصنوعی در مسیر زیر یافت نشد:\n{BONE_WEIGHTS_PATH}")
            return False

        try:
            self.status_label.config(text="⏳ در حال بارگذاری مدل هوش مصنوعی در حافظه...", fg=C_CYAN)
            self.update_idletasks()
            dev = torch.device(self.device)
            self.bone_model = torch.jit.load(BONE_WEIGHTS_PATH, map_location=dev).eval()
            if os.path.exists(LUNG_WEIGHTS_PATH):
                self.lung_model = torch.jit.load(LUNG_WEIGHTS_PATH, map_location=dev).eval()
            self.status_label.config(text=f"● مدل‌ها در حافظه بارگذاری شدند ({self.device.upper()})", fg="#10b981")
            return True
        except Exception as e:
            messagebox.showerror("خطای بارگذاری مدل", str(e))
            self.status_label.config(text=f"خطا در بارگذاری مدل: {e}", fg=C_RED_HOVER)
            return False

    def on_device_change(self, event=None):
        self.device = self.dev_combo.get()
        self.bone_model = None
        self.lung_model = None
        self.status_label.config(text=f"سخت‌افزار پردازش تغییر یافت: {self.device.upper()}", fg=C_CYAN)

    def open_image(self):
        filetypes = [
            ("All Supported Formats", "*.png;*.jpg;*.jpeg;*.tif;*.tiff;*.dcm;*.bmp"),
            ("DICOM Medical Files (*.dcm)", "*.dcm"),
            ("PNG / JPEG Images", "*.png;*.jpg;*.jpeg"),
            ("All Files", "*.*")
        ]
        path = filedialog.askopenfilename(title="انتخاب تصویر رادیوگرافی قفسه سینه", filetypes=filetypes)
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
            fn = os.path.basename(path)
            self.status_label.config(text=f"✓ فایل بارگذاری شد: {fn} ({arr.shape[1]}x{arr.shape[0]})", fg=C_TEXT_LIGHT)
            self.render_view()
        except Exception as e:
            messagebox.showerror("خطا در باز کردن تصویر", str(e))

    def read_image(self, path):
        if path.lower().endswith(".dcm"):
            if not pydicom:
                raise RuntimeError("کتابخانه pydicom برای پردازش فایل‌های .dcm مورد نیاز است.")
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
        self.status_label.config(text="⏳ در حال استنباط شبکه عصبی و تفکیک استخوان...", fg=C_CYAN)
        self.update_idletasks()

        arr = self.original_np.copy()
        if self.auto_invert_var.get() and self.looks_inverted(arr):
            arr = arr.max() - arr

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

    def on_slider_click(self, event):
        cw = self.canvas.winfo_width()
        if cw > 0:
            self.slider_pos.set(max(0.0, min(1.0, event.x / cw)))
            self.render_view()

    def on_resize(self, event=None):
        self.render_view()

    def render_view(self):
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw <= 10 or ch <= 10:
            return

        if self.original_np is None:
            self.canvas.delete("all")
            cx, cy = cw // 2, ch // 2
            card_w, card_h = min(680, cw - 60), min(340, ch - 60)
            x1, y1 = cx - card_w // 2, cy - card_h // 2
            x2, y2 = cx + card_w // 2, cy + card_h // 2

            self.canvas.create_rectangle(x1, y1, x2, y2, fill=C_CARD, outline=C_BORDER, width=1)
            self.canvas.create_text(cx, cy - 80, text="🫁", font=("Segoe UI", 36), fill=C_CYAN)
            self.canvas.create_text(cx, cy - 30, text="سامانه هوشمند حذف استخوان در رادیوگرافی قفسه سینه",
                                    font=("Segoe UI", 13, "bold"), fill=C_TEXT_LIGHT)
            self.canvas.create_text(cx, cy, text="BoneSuppression AI - Chest Radiograph Studio",
                                    font=("Segoe UI", 10), fill=C_TEXT_MUTED)

            self.canvas.create_text(cx, cy + 38, text="جهت شروع، روی دکمه «باز کردن تصویر / DICOM» در نوار بالا کلیک کنید",
                                    font=("Segoe UI", 10, "bold"), fill=C_CYAN)
            self.canvas.create_text(cx, cy + 68, text="پشتیبانی از فرمت‌های پزشکی: DICOM (.dcm) | PNG | JPEG | TIFF",
                                    font=("Segoe UI", 8), fill=C_TEXT_DIM)

            self.canvas.create_text(cx, cy + 110,
                                    text=f"{HOSPITAL_TITLE} - {NETWORK_TITLE} | توسعه: {DEVELOPER_NAME}",
                                    font=("Segoe UI", 8), fill=C_TEXT_DIM)
            return

        mode = self.view_mode.get()
        orig_img = self.to_display_image(self.original_np)
        soft_img = self.to_display_image(self.soft_np) if self.soft_np is not None else orig_img

        if mode == "split":
            img_w, img_h = orig_img.size
            scale = min((cw - 24) / img_w, (ch - 24) / img_h)
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

            line_x = ox + split_x
            self.canvas.create_line(line_x, oy, line_x, oy + nh, fill=C_CYAN, width=2)
            self.canvas.create_oval(line_x - 10, oy + nh // 2 - 10, line_x + 10, oy + nh // 2 + 10,
                                   fill=C_CYAN, outline="#ffffff", width=2)

            self.canvas.create_rectangle(ox + 10, oy + 10, ox + 175, oy + 38, fill="#0b0f19", outline=C_BORDER)
            self.canvas.create_text(ox + 18, oy + 17, text="تصویر اصلی (Original)", fill="white", anchor=tk.NW, font=("Segoe UI", 9, "bold"))

            self.canvas.create_rectangle(ox + nw - 200, oy + 10, ox + nw - 10, oy + 38, fill="#0b0f19", outline=C_BORDER)
            self.canvas.create_text(ox + nw - 192, oy + 17, text="حذف استخوان (Soft Tissue)", fill=C_CYAN, anchor=tk.NW, font=("Segoe UI", 9, "bold"))

        elif mode == "dual":
            half_w = (cw - 30) // 2
            img_w, img_h = orig_img.size
            scale = min(half_w / img_w, (ch - 24) / img_h)
            nw, nh = int(img_w * scale), int(img_h * scale)
            oy = (ch - nh) // 2

            r_orig = orig_img.resize((nw, nh), Image.Resampling.BILINEAR)
            r_soft = soft_img.resize((nw, nh), Image.Resampling.BILINEAR)

            self.tk_orig = ImageTk.PhotoImage(r_orig)
            self.tk_soft = ImageTk.PhotoImage(r_soft)

            self.canvas.delete("all")
            self.canvas.create_image(10, oy, anchor=tk.NW, image=self.tk_orig)
            self.canvas.create_image(20 + nw, oy, anchor=tk.NW, image=self.tk_soft)

            self.canvas.create_rectangle(15, oy + 10, 205, oy + 36, fill="#0b0f19", outline=C_BORDER)
            self.canvas.create_text(22, oy + 16, text="تصویر کامل (Full Radiograph)", fill="white", anchor=tk.NW, font=("Segoe UI", 9, "bold"))

            self.canvas.create_rectangle(25 + nw, oy + 10, 265 + nw, oy + 36, fill="#0b0f19", outline=C_BORDER)
            self.canvas.create_text(32 + nw, oy + 16, text="بافت نرم - حذف استخوان (Soft Tissue)", fill=C_CYAN, anchor=tk.NW, font=("Segoe UI", 9, "bold"))

        elif mode == "quad":
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

            self.canvas.create_text(20, 20, text="Full Radiograph (CXR)", fill="white", anchor=tk.NW, font=("Segoe UI", 9, "bold"))
            self.canvas.create_text(30 + nw, 20, text="Predicted Bone (استخوان)", fill=C_AMBER, anchor=tk.NW, font=("Segoe UI", 9, "bold"))
            self.canvas.create_text(20, 30 + nh, text="Bone-Suppressed (بافت نرم)", fill="#10b981", anchor=tk.NW, font=("Segoe UI", 9, "bold"))
            self.canvas.create_text(30 + nw, 30 + nh, text="Lung Component (میدان ریه)", fill=C_CYAN, anchor=tk.NW, font=("Segoe UI", 9, "bold"))

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


def handle_fatal_exception(exc_type, exc_val, exc_tb):
    """Crash handler: logs to disk and presents standard dialog."""
    err_text = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
    log_file = os.path.join(EXE_DIR, "bone_suppression_error.log")
    try:
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(err_text)
    except Exception:
        pass
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "خطای اجرای نرم‌افزار",
            f"متأسفانه در اجرای برنامه خطایی رخ داده است:\n\n{str(exc_val)}\n\n"
            f"گزارش خطا در فایل زیر ذخیره شد:\n{log_file}"
        )
    except Exception:
        pass


if __name__ == "__main__":
    sys.excepthook = handle_fatal_exception
    try:
        app = BoneSuppressionApp()
        app.mainloop()
    except Exception as exc:
        handle_fatal_exception(type(exc), exc, exc.__traceback__)
