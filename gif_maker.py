import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import os
import sys
import subprocess
import threading
from datetime import datetime

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False

BG      = "#0a0a0a"
CARD    = "#161616"
BORDER  = "#2a2a2a"
ACTIVE  = "#ffffff"
TEXT    = "#ffffff"
SUBTEXT = "#888888"
MUTED   = "#555555"
BTN_BG  = "#ffffff"
BTN_FG  = "#0a0a0a"
SUCCESS = "#4ade80"
ERROR   = "#f87171"

if sys.platform == "darwin":
    FONT = "Apple SD Gothic Neo"
else:
    FONT = "맑은 고딕"

SIZES = [
    ("정방형\n800 × 800",  800, 800),
    ("세로형\n640 × 768",  640, 768),
]
DELAYS = [300, 500, 700, 1000, 1200]


def get_gifsicle_path():
    exe = "gifsicle.exe" if sys.platform == "win32" else "gifsicle"
    if hasattr(sys, "_MEIPASS"):
        p = os.path.join(sys._MEIPASS, exe)
        if os.path.exists(p):
            return p
    return exe


class GifMakerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("제품 GIF 메이커")
        self.root.geometry("500x740")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        self.image_paths = []
        self.thumbnails = []
        self.is_processing = False
        self.size_idx = 0

        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self.root, bg=BG)
        hdr.pack(fill="x", padx=24, pady=(28, 0))
        tk.Label(hdr, text="제품 GIF 메이커", font=(FONT, 18, "bold"),
                 bg=BG, fg=TEXT).pack(side="left")
        tk.Label(hdr, text="쇼핑몰 상세페이지용 · 사진 3~5장 → GIF",
                 font=(FONT, 10), bg=BG, fg=SUBTEXT).pack(side="left", padx=(10, 0), pady=(5, 0))

        self._section("① 사진 추가", top=20)
        self._build_dropzone()

        self.thumb_frame = tk.Frame(self.root, bg=BG)
        self.thumb_frame.pack(padx=24, pady=(8, 0), anchor="w")

        self._section("② 출력 사이즈", top=20)
        self._build_size_pills()

        self._section("③ 여백 처리", top=20)
        self._build_fit_pills()

        self._section("④ 전환 속도", top=20)
        self._build_speed_slider()

        self.btn_make = tk.Button(
            self.root, text="GIF 만들기",
            command=self.start_make,
            bg=BTN_BG, fg=BTN_FG,
            font=(FONT, 13, "bold"),
            relief="flat", bd=0, pady=14,
            cursor="hand2",
            activebackground="#e5e5e5", activeforeground=BTN_FG,
            state="disabled",
        )
        self.btn_make.pack(fill="x", padx=24, pady=(24, 0))

        self.lbl_status = tk.Label(
            self.root, text="먼저 사진을 추가해주세요",
            font=(FONT, 10), bg=BG, fg=SUBTEXT
        )
        self.lbl_status.pack(pady=(10, 0))

    def _section(self, text, top=16):
        tk.Label(self.root, text=text,
                 font=(FONT, 10, "bold"), bg=BG, fg=SUBTEXT
                 ).pack(anchor="w", padx=24, pady=(top, 4))

    def _build_dropzone(self):
        outer = tk.Frame(self.root, bg=BG)
        outer.pack(fill="x", padx=24)

        self.dz_canvas = tk.Canvas(
            outer, width=452, height=120,
            bg=CARD, highlightthickness=0, cursor="hand2"
        )
        self.dz_canvas.pack()
        self._draw_dz(active=False)

        self.dz_text = tk.Label(
            self.dz_canvas,
            text="사진 3~5장을 끌어다 놓으세요",
            font=(FONT, 11), bg=CARD, fg=SUBTEXT, cursor="hand2"
        )
        self.dz_sub = tk.Label(
            self.dz_canvas,
            text="JPG · PNG · WEBP  |  클릭해서 파일 선택",
            font=(FONT, 9), bg=CARD, fg=MUTED, cursor="hand2"
        )
        self.dz_canvas.create_window(226, 52, window=self.dz_text)
        self.dz_canvas.create_window(226, 76, window=self.dz_sub)

        for w in (self.dz_canvas, self.dz_text, self.dz_sub):
            w.bind("<Button-1>", self._open_file_dialog)

        if HAS_DND:
            for w in (self.dz_canvas, self.dz_text, self.dz_sub):
                w.drop_target_register(DND_FILES)
                w.dnd_bind("<<Drop>>", self._on_drop)
                w.dnd_bind("<<DragEnter>>", lambda e: self._draw_dz(active=True))
                w.dnd_bind("<<DragLeave>>", lambda e: self._draw_dz(active=False))

    def _draw_dz(self, active=False):
        self.dz_canvas.delete("border")
        color = SUCCESS if active else BORDER
        dash = () if active else (10, 5)
        self.dz_canvas.create_rectangle(
            4, 4, 448, 116,
            outline=color, dash=dash, width=2, tags="border"
        )

    def _open_file_dialog(self, event=None):
        from tkinter import filedialog
        files = filedialog.askopenfilenames(
            title="사진 선택 (3~5장)",
            filetypes=[("이미지", "*.jpg *.jpeg *.png *.webp")]
        )
        if files:
            self._handle_files(list(files))

    def _on_drop(self, event):
        files = self.root.tk.splitlist(event.data)
        valid = [f for f in files if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
        self._handle_files(valid)

    def _handle_files(self, files):
        if not files:
            self._set_status("이미지 파일만 사용할 수 있어요", ERROR)
            return
        if len(files) < 3 or len(files) > 5:
            self._set_status(f"{len(files)}장 선택됨 · 3~5장만 가능해요", ERROR)
            return

        self.image_paths = files
        self._draw_dz(active=True)
        self.dz_text.config(text=f"{len(files)}장 준비 완료", fg=TEXT)
        self.dz_sub.config(text="다시 끌어다 놓으면 교체", fg=SUBTEXT)
        self._set_status("준비 완료 · GIF 만들기 버튼을 눌러주세요", SUCCESS)
        self.btn_make.config(state="normal")
        self._render_thumbs()

    def _render_thumbs(self):
        for w in self.thumb_frame.winfo_children():
            w.destroy()
        self.thumbnails.clear()
        for path in self.image_paths:
            try:
                img = Image.open(path)
                img.thumbnail((64, 64))
                photo = ImageTk.PhotoImage(img)
                self.thumbnails.append(photo)
                tk.Label(self.thumb_frame, image=photo, bg=CARD, bd=0).pack(side="left", padx=4)
            except Exception:
                pass

    def _build_size_pills(self):
        frame = tk.Frame(self.root, bg=BG)
        frame.pack(fill="x", padx=24)
        self.pill_btns = []
        for i, (label, w, h) in enumerate(SIZES):
            btn = tk.Button(
                frame, text=label,
                command=lambda idx=i: self._select_size(idx),
                font=(FONT, 10), relief="flat", bd=0,
                pady=10, cursor="hand2", wraplength=160,
            )
            btn.pack(side="left", expand=True, fill="both", padx=(0, 4 if i == 0 else 0))
            self.pill_btns.append(btn)
        self._select_size(0)

    def _select_size(self, idx):
        self.size_idx = idx
        for i, btn in enumerate(self.pill_btns):
            if i == idx:
                btn.config(bg=TEXT, fg=BG, activebackground="#e5e5e5", activeforeground=BG)
            else:
                btn.config(bg=CARD, fg=SUBTEXT, activebackground=CARD, activeforeground=TEXT)

    def _build_fit_pills(self):
        frame = tk.Frame(self.root, bg=BG)
        frame.pack(fill="x", padx=24)
        self.fit_idx = 0
        self.fit_btns = []
        for i, label in enumerate(["꽉 채우기\n(잘라내기)", "비율 유지\n(흰 여백)"]):
            btn = tk.Button(
                frame, text=label,
                command=lambda idx=i: self._select_fit(idx),
                font=(FONT, 10), relief="flat", bd=0,
                pady=10, cursor="hand2", wraplength=160,
            )
            btn.pack(side="left", expand=True, fill="both", padx=(0, 4 if i == 0 else 0))
            self.fit_btns.append(btn)
        self._select_fit(0)

    def _select_fit(self, idx):
        self.fit_idx = idx
        for i, btn in enumerate(self.fit_btns):
            if i == idx:
                btn.config(bg=TEXT, fg=BG, activebackground="#e5e5e5", activeforeground=BG)
            else:
                btn.config(bg=CARD, fg=SUBTEXT, activebackground=CARD, activeforeground=TEXT)

    def _build_speed_slider(self):
        card = tk.Frame(self.root, bg=CARD)
        card.pack(fill="x", padx=24)

        row = tk.Frame(card, bg=CARD)
        row.pack(fill="x", padx=16, pady=(12, 0))
        tk.Label(row, text="빠름", font=(FONT, 9), bg=CARD, fg=MUTED).pack(side="left")
        tk.Label(row, text="느림", font=(FONT, 9), bg=CARD, fg=MUTED).pack(side="right")

        self.slider = tk.Scale(
            card, from_=0, to=4, orient="horizontal",
            showvalue=0, command=self._update_speed_label,
            length=420, bg=CARD, fg=TEXT,
            troughcolor=BORDER, highlightthickness=0,
            bd=0, sliderlength=20, sliderrelief="flat"
        )
        self.slider.set(3)
        self.slider.pack(padx=12, pady=(0, 4))

        self.lbl_speed = tk.Label(
            card, text="1.0초마다 전환",
            font=(FONT, 10), bg=CARD, fg=TEXT
        )
        self.lbl_speed.pack(pady=(0, 12))

    def _update_speed_label(self, val):
        ms = DELAYS[int(val)]
        self.lbl_speed.config(text=f"{ms/1000:.1f}초마다 전환")

    def _set_status(self, text, color=None):
        self.lbl_status.config(text=text, fg=color or SUBTEXT)

    def start_make(self):
        if self.is_processing or not self.image_paths:
            return
        self.is_processing = True
        self.btn_make.config(state="disabled", text="처리 중...", bg="#888888")
        self._set_status("이미지 리사이즈 중...")

        _, w, h = SIZES[self.size_idx]
        fit_mode = self.fit_idx  # 0=crop, 1=letterbox
        delay_ms = DELAYS[int(self.slider.get())]
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        save_path = os.path.join(desktop, f"my_gif_{ts}.gif")

        threading.Thread(
            target=self._worker, args=(w, h, fit_mode, delay_ms, save_path, desktop),
            daemon=True
        ).start()

    def _worker(self, w, h, fit_mode, delay_ms, save_path, desktop):
        try:
            frames = []
            for i, path in enumerate(self.image_paths):
                img = Image.open(path).convert("RGB")
                if fit_mode == 0:  # crop to fill
                    ratio = max(w / img.width, h / img.height)
                    nw, nh = int(img.width * ratio), int(img.height * ratio)
                    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
                    left, top = (nw - w) // 2, (nh - h) // 2
                    img = img.crop((left, top, left + w, top + h))
                else:  # letterbox with white background
                    ratio = min(w / img.width, h / img.height)
                    nw, nh = int(img.width * ratio), int(img.height * ratio)
                    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
                    canvas = Image.new("RGB", (w, h), (255, 255, 255))
                    canvas.paste(img, ((w - nw) // 2, (h - nh) // 2))
                    img = canvas
                frames.append(img)
                self.root.after(0, self._set_status, f"리사이즈 중... ({i+1}/{len(self.image_paths)})")

            self.root.after(0, self._set_status, "색상 최적화 중...")
            quantized = []
            for f in frames:
                try:
                    qf = f.quantize(colors=256, method=Image.Quantize.LIBIMAGEQUANT,
                                    dither=Image.Dither.FLOYDSTEINBERG)
                except (ValueError, OSError):
                    qf = f.quantize(colors=256, method=Image.Quantize.MEDIANCUT,
                                    dither=Image.Dither.FLOYDSTEINBERG)
                quantized.append(qf)

            self.root.after(0, self._set_status, "GIF 저장 중...")
            tmp = save_path + ".tmp.gif"
            quantized[0].save(
                tmp, format="GIF",
                append_images=quantized[1:], save_all=True,
                duration=delay_ms, loop=0, optimize=True, disposal=2,
            )

            self.root.after(0, self._set_status, "압축 최적화 중...")
            gifsicle = get_gifsicle_path()
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            try:
                subprocess.run(
                    [gifsicle, "-O3", "--lossy=100", "--careful", tmp, "-o", save_path],
                    check=True, capture_output=True, timeout=60, creationflags=flags,
                )
                os.remove(tmp)
            except Exception:
                os.replace(tmp, save_path)

            size_mb = os.path.getsize(save_path) / (1024 * 1024)
            self.root.after(0, self._on_success, save_path, size_mb)

        except Exception as e:
            self.root.after(0, self._on_error, str(e))

    def _on_success(self, save_path, size_mb):
        self.is_processing = False
        self.btn_make.config(state="normal", text="GIF 만들기", bg=BTN_BG)
        if size_mb > 2.0:
            self._set_status(f"✓ 저장 완료 · {size_mb:.2f} MB (2MB 초과 — 사진 수 줄이거나 속도 높이세요)", ERROR)
        else:
            self._set_status(f"✓ 저장 완료 · {size_mb:.2f} MB · 바탕화면 확인", SUCCESS)
        if sys.platform == "darwin":
            subprocess.run(["open", "-R", save_path], check=False)
        elif sys.platform == "win32":
            subprocess.run(["explorer", "/select,", save_path], check=False)

    def _on_error(self, msg):
        self.is_processing = False
        self.btn_make.config(state="normal", text="GIF 만들기", bg=BTN_BG)
        self._set_status("오류가 발생했어요", ERROR)
        messagebox.showerror("오류", msg)


if __name__ == "__main__":
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = GifMakerApp(root)
    root.mainloop()
