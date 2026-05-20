import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import os
import sys
import subprocess
import threading
from datetime import datetime

from tkinterdnd2 import TkinterDnD, DND_FILES

# ── 색상 팔레트 (다크 미니멀) ──────────────────────────────────────
BG       = "#111111"
CARD     = "#1c1c1c"
BORDER   = "#333333"
TEXT     = "#ffffff"
SUBTEXT  = "#888888"
BTN_BG   = "#ffffff"
BTN_FG   = "#111111"
SUCCESS  = "#4ade80"
ERROR    = "#f87171"
FONT     = "맑은 고딕"


def get_gifsicle_path():
    exe_name = 'gifsicle.exe' if sys.platform == 'win32' else 'gifsicle'
    if hasattr(sys, '_MEIPASS'):
        bundled = os.path.join(sys._MEIPASS, exe_name)
        if os.path.exists(bundled):
            return bundled
    return exe_name


def card_frame(parent, **kw):
    return tk.Frame(parent, bg=CARD, **kw)


class GifMakerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GIF 메이커")
        self.root.geometry("460x720")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        self.image_paths = []
        self.thumbnails = []
        self.is_processing = False

        self._build_ui()

    # ── UI 구성 ────────────────────────────────────────────────────
    def _build_ui(self):
        pad = dict(padx=20, pady=0)

        # 헤더
        hdr = tk.Frame(self.root, bg=BG)
        hdr.pack(fill="x", padx=20, pady=(24, 0))
        tk.Label(hdr, text="GIF 메이커", font=(FONT, 18, "bold"),
                 bg=BG, fg=TEXT).pack(side="left")
        tk.Label(hdr, text="패션 상품용", font=(FONT, 11),
                 bg=BG, fg=SUBTEXT).pack(side="left", padx=(10, 0), pady=(4, 0))

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x", padx=20, pady=14)

        # 1. 드롭존 ─────────────────────────────────────────────
        self._section_label("① 사진 추가  (3~5장)")

        drop_outer = card_frame(self.root)
        drop_outer.pack(fill="x", **pad, pady=(6, 0))

        self.canvas_drop = tk.Canvas(
            drop_outer, width=420, height=110,
            bg=CARD, highlightthickness=0
        )
        self.canvas_drop.pack(padx=0, pady=0)
        self._draw_drop_zone(active=False)

        self.lbl_drop_text = tk.Label(
            self.canvas_drop,
            text="여기에 사진을 드래그 앤 드롭 하세요",
            font=(FONT, 11), bg=CARD, fg=SUBTEXT
        )
        self.canvas_drop.create_window(210, 55, window=self.lbl_drop_text)

        # DnD 등록
        for w in (self.canvas_drop, self.lbl_drop_text):
            w.drop_target_register(DND_FILES)
            w.dnd_bind('<<Drop>>', self.handle_drop)

        # 상태 + 썸네일
        self.lbl_status = tk.Label(
            self.root, text="아직 이미지가 없어요",
            font=(FONT, 10), bg=BG, fg=SUBTEXT
        )
        self.lbl_status.pack(pady=(10, 0))

        self.preview_frame = tk.Frame(self.root, bg=BG)
        self.preview_frame.pack(pady=(6, 0))

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x", padx=20, pady=14)

        # 2. 사이즈 ────────────────────────────────────────────
        self._section_label("② 출력 사이즈")

        size_card = card_frame(self.root)
        size_card.pack(fill="x", **pad, pady=(6, 0))

        self.size_var = tk.StringVar(value="1200x1200")
        for val, label in [("1200x1200", "정방형  1200 × 1200"), ("960x1152", "세로형  960 × 1152")]:
            rb = tk.Radiobutton(
                size_card, text=label, variable=self.size_var, value=val,
                font=(FONT, 10), bg=CARD, fg=TEXT,
                selectcolor=CARD, activebackground=CARD, activeforeground=TEXT,
                indicatoron=0,
                relief="flat", bd=0,
                width=22, pady=8,
                cursor="hand2"
            )
            rb.pack(side="left", expand=True, fill="both", padx=1, pady=1)
            rb.bind("<Enter>", lambda e, w=rb: w.config(fg=TEXT))

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x", padx=20, pady=14)

        # 3. 속도 ──────────────────────────────────────────────
        self._section_label("③ 전환 속도")

        speed_card = card_frame(self.root)
        speed_card.pack(fill="x", **pad, pady=(6, 0))

        self.delays = [0.3, 0.5, 0.7, 1.0, 1.2]
        labels_row = tk.Frame(speed_card, bg=CARD)
        labels_row.pack(fill="x", padx=16, pady=(12, 0))
        for lbl in ["빠름", "", "", "", "느림"]:
            tk.Label(labels_row, text=lbl, font=(FONT, 9), bg=CARD,
                     fg=SUBTEXT).pack(side="left", expand=True)

        self.slider = tk.Scale(
            speed_card, from_=0, to=4, orient=tk.HORIZONTAL,
            showvalue=0, command=self.update_slider_label,
            length=380, bg=CARD, fg=TEXT,
            troughcolor=BORDER, highlightthickness=0,
            bd=0, sliderlength=20, sliderrelief="flat"
        )
        self.slider.set(3)
        self.slider.pack(padx=14, pady=(0, 4))

        self.lbl_delay = tk.Label(
            speed_card, text="1.0초마다 전환",
            font=(FONT, 10), bg=CARD, fg=TEXT
        )
        self.lbl_delay.pack(pady=(0, 12))

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x", padx=20, pady=14)

        # 4. CTA 버튼 ──────────────────────────────────────────
        self.btn_make = tk.Button(
            self.root,
            text="GIF 만들기",
            command=self.start_make_gif,
            bg=BTN_BG, fg=BTN_FG,
            font=(FONT, 13, "bold"),
            relief="flat", bd=0,
            cursor="hand2",
            pady=14,
            activebackground="#e5e5e5",
            activeforeground=BTN_FG,
        )
        self.btn_make.pack(fill="x", padx=20, pady=(0, 6))

        self.lbl_progress = tk.Label(
            self.root, text="",
            font=(FONT, 10), bg=BG, fg=SUBTEXT
        )
        self.lbl_progress.pack(pady=(0, 16))

    def _section_label(self, text):
        tk.Label(self.root, text=text, font=(FONT, 11, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w", padx=20, pady=(0, 0))

    def _draw_drop_zone(self, active=False):
        self.canvas_drop.delete("border")
        color = TEXT if active else BORDER
        self.canvas_drop.create_rectangle(
            6, 6, 414, 104,
            outline=color, dash=(10, 5), width=2, tags="border"
        )

    # ── 드롭 핸들 ─────────────────────────────────────────────────
    def handle_drop(self, event):
        files = self.root.tk.splitlist(event.data)
        valid_exts = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
        valid_files = [f for f in files if f.lower().endswith(valid_exts)]

        if not valid_files:
            messagebox.showwarning("경고", "이미지 파일만 드롭해주세요.")
            return
        if len(valid_files) < 3 or len(valid_files) > 5:
            messagebox.showwarning("경고", f"{len(valid_files)}장 선택됨. 3~5장만 가능해요.")
            return

        self.image_paths = valid_files
        self.lbl_status.config(
            text=f"✓  {len(self.image_paths)}장 선택됨", fg=SUCCESS
        )
        self._draw_drop_zone(active=True)
        self.lbl_drop_text.config(
            text=f"사진 {len(self.image_paths)}장 준비 완료  —  다시 드롭하면 교체",
            fg=TEXT
        )
        self.update_previews()

    def update_previews(self):
        for w in self.preview_frame.winfo_children():
            w.destroy()
        self.thumbnails.clear()

        for path in self.image_paths:
            try:
                img = Image.open(path)
                img.thumbnail((72, 72))
                photo = ImageTk.PhotoImage(img)
                self.thumbnails.append(photo)

                thumb_frame = tk.Frame(self.preview_frame, bg=CARD, padx=2, pady=2)
                thumb_frame.pack(side=tk.LEFT, padx=4)
                tk.Label(thumb_frame, image=photo, bg=CARD).pack()
            except Exception:
                pass

    def update_slider_label(self, val):
        idx = int(val)
        self.lbl_delay.config(text=f"{self.delays[idx]}초마다 전환")

    # ── GIF 생성 (스레드) ──────────────────────────────────────────
    def start_make_gif(self):
        if self.is_processing:
            return
        if not self.image_paths:
            messagebox.showerror("오류", "먼저 이미지를 드롭해주세요.")
            return

        self.is_processing = True
        self.btn_make.config(state="disabled", text="GIF 생성 중...", bg="#888888")
        self.lbl_progress.config(text="이미지 처리 중...", fg=SUBTEXT)

        w, h = map(int, self.size_var.get().split('x'))
        idx = int(self.slider.get())
        delay_ms = int(self.delays[idx] * 1000)
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        save_path = os.path.join(desktop, f"my_gif_{timestamp}.gif")

        threading.Thread(
            target=self._make_gif_worker,
            args=(w, h, delay_ms, desktop, save_path, timestamp),
            daemon=True
        ).start()

    def _make_gif_worker(self, w, h, delay_ms, desktop, save_path, timestamp):
        try:
            self._progress("이미지 리사이즈 중...")
            frames = []
            for path in self.image_paths:
                img = Image.open(path).convert('RGB')
                img_w, img_h = img.size
                ratio = max(w / img_w, h / img_h)
                new_w, new_h = int(img_w * ratio), int(img_h * ratio)
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                left = (new_w - w) / 2
                top  = (new_h - h) / 2
                img  = img.crop((left, top, left + w, top + h))
                frames.append(img)

            self._progress("색상 최적화 중...")
            quantized = []
            for f in frames:
                try:
                    qf = f.quantize(colors=256, method=Image.Quantize.LIBIMAGEQUANT,
                                    dither=Image.Dither.FLOYDSTEINBERG)
                except (ValueError, OSError):
                    qf = f.quantize(colors=256, method=Image.Quantize.MEDIANCUT,
                                    dither=Image.Dither.FLOYDSTEINBERG)
                quantized.append(qf)

            self._progress("GIF 저장 중...")
            temp_path = save_path + '.tmp.gif'
            quantized[0].save(
                temp_path, format='GIF',
                append_images=quantized[1:], save_all=True,
                duration=delay_ms, loop=0, optimize=True, disposal=2,
            )

            self._progress("압축 최적화 중...")
            gifsicle = get_gifsicle_path()
            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            try:
                subprocess.run(
                    [gifsicle, '-O3', '--lossy=80', '--careful', temp_path, '-o', save_path],
                    check=True, capture_output=True, timeout=60, creationflags=creationflags,
                )
                os.remove(temp_path)
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                os.replace(temp_path, save_path)

            file_size_mb = os.path.getsize(save_path) / (1024 * 1024)
            self.root.after(0, self._on_success, save_path, file_size_mb, desktop, timestamp)

        except Exception as e:
            self.root.after(0, self._on_error, str(e))

    def _progress(self, msg):
        self.root.after(0, lambda: self.lbl_progress.config(text=msg, fg=SUBTEXT))

    def _on_success(self, save_path, size_mb, desktop, timestamp):
        self.is_processing = False
        self.btn_make.config(state="normal", text="GIF 만들기", bg=BTN_BG)
        self.lbl_progress.config(
            text=f"✓  저장 완료  {size_mb:.2f} MB", fg=SUCCESS
        )
        messagebox.showinfo(
            "저장 완료",
            f"GIF가 바탕화면에 저장됐어요!\n\n파일: my_gif_{timestamp}.gif\n용량: {size_mb:.2f} MB\n위치: {save_path}"
        )
        if sys.platform == 'win32':
            os.startfile(desktop)
        elif sys.platform == 'darwin':
            subprocess.run(['open', desktop], check=False)

    def _on_error(self, msg):
        self.is_processing = False
        self.btn_make.config(state="normal", text="GIF 만들기", bg=BTN_BG)
        self.lbl_progress.config(text="오류가 발생했어요", fg=ERROR)
        messagebox.showerror("오류", f"GIF 생성 중 문제가 생겼어요:\n{msg}")


if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = GifMakerApp(root)
    root.mainloop()
