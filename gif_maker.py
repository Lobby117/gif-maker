import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import os
from datetime import datetime

# 드래그 앤 드롭 라이브러리
from tkinterdnd2 import TkinterDnD, DND_FILES

class GifMakerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("나만의 GIF 메이커 (드래그 & 드롭)")
        self.root.geometry("450x650") # 미리보기를 위해 세로로 살짝 길게 변경

        self.image_paths = []
        self.thumbnails = [] # 썸네일 이미지가 화면에서 사라지지 않게 보관하는 리스트

        # 1. 드래그 앤 드롭 영역
        tk.Label(root, text="[ 1. 이미지 추가 (3~5장) ]", font=("맑은 고딕", 12, "bold")).pack(pady=(15, 5))
        
        self.drop_frame = tk.Frame(root, bg="#e0e0e0", width=350, height=80, relief="sunken", bd=2)
        self.drop_frame.pack_propagate(False) # 프레임 크기 고정
        self.drop_frame.pack(pady=5)
        
        self.lbl_drop = tk.Label(self.drop_frame, text="📸 여기에 사진(3~5장)을 드래그 앤 드롭 하세요!", bg="#e0e0e0", font=("맑은 고딕", 10))
        self.lbl_drop.pack(expand=True)

        # 드래그 앤 드롭 이벤트 연결
        self.drop_frame.drop_target_register(DND_FILES)
        self.drop_frame.dnd_bind('<<Drop>>', self.handle_drop)
        self.lbl_drop.drop_target_register(DND_FILES)
        self.lbl_drop.dnd_bind('<<Drop>>', self.handle_drop)

        self.lbl_status = tk.Label(root, text="선택된 이미지: 0장", fg="blue")
        self.lbl_status.pack()

        # --- 미리보기 영역 (썸네일이 나타날 곳) ---
        self.preview_frame = tk.Frame(root)
        self.preview_frame.pack(pady=10)

        # 2. 출력 사이즈 선택
        tk.Label(root, text="[ 2. 출력 사이즈 선택 ]", font=("맑은 고딕", 12, "bold")).pack(pady=(15, 5))
        self.size_var = tk.StringVar(value="1200x1200")
        tk.Radiobutton(root, text="정방형 (1200 x 1200)", variable=self.size_var, value="1200x1200").pack()
        tk.Radiobutton(root, text="세로형 (960 x 1152)", variable=self.size_var, value="960x1152").pack()

        # 3. 속도 조절 (슬라이드바)
        tk.Label(root, text="[ 3. 사진 변경 속도 조절 ]", font=("맑은 고딕", 12, "bold")).pack(pady=(15, 5))
        
        self.delays = [0.3, 0.5, 0.7, 1.0, 1.2]
        self.slider = tk.Scale(root, from_=0, to=4, orient=tk.HORIZONTAL, showvalue=0, command=self.update_slider_label, length=200)
        self.slider.set(3) # 기본값을 1.0초로
        self.slider.pack()
        self.lbl_delay = tk.Label(root, text="현재 속도: 1.0초", font=("맑은 고딕", 10))
        self.lbl_delay.pack()

        # 4. 완성 버튼
        tk.Label(root, text="[ 4. 완성하기 ]", font=("맑은 고딕", 12, "bold")).pack(pady=(15, 5))
        self.btn_make = tk.Button(root, text="GIF 만들기 (바탕화면 자동 저장)", command=self.make_gif, bg="black", fg="white", font=("맑은 고딕", 10, "bold"))
        self.btn_make.pack()

    def handle_drop(self, event):
        # 드롭된 파일 경로들을 리스트로 변환 (Mac 특성 대응)
        files = self.root.tk.splitlist(event.data)
        
        # 이미지 파일만 필터링
        valid_exts = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
        valid_files = [f for f in files if f.lower().endswith(valid_exts)]
        
        if not valid_files:
            messagebox.showwarning("경고", "이미지 파일만 드롭해주세요.")
            return
            
        if len(valid_files) < 3 or len(valid_files) > 5:
            messagebox.showwarning("경고", f"현재 {len(valid_files)}장입니다. 3장에서 5장 사이로 드롭해주세요!")
            return
            
        self.image_paths = valid_files
        self.lbl_status.config(text=f"선택된 이미지: {len(self.image_paths)}장")
        
        # 사진을 올리면 썸네일 미리보기 생성
        self.update_previews()

    def update_previews(self):
        # 기존에 있던 썸네일 지우기
        for widget in self.preview_frame.winfo_children():
            widget.destroy()
        self.thumbnails.clear()
        
        # 새 썸네일 만들기
        for path in self.image_paths:
            try:
                img = Image.open(path)
                img.thumbnail((60, 60)) # 미리보기 사이즈 조절 (정비율 축소)
                photo = ImageTk.PhotoImage(img)
                self.thumbnails.append(photo) # 화면에서 안 날아가게 보관
                
                # 라벨에 이미지 넣어서 화면에 표시
                lbl = tk.Label(self.preview_frame, image=photo, relief="solid", bd=1)
                lbl.pack(side=tk.LEFT, padx=3)
            except Exception as e:
                print(f"미리보기 오류: {e}")

    def update_slider_label(self, val):
        idx = int(val)
        self.lbl_delay.config(text=f"현재 속도: {self.delays[idx]}초")

    def make_gif(self):
        if not self.image_paths:
            messagebox.showerror("오류", "먼저 이미지를 영역에 드롭해주세요.")
            return

        w, h = map(int, self.size_var.get().split('x'))
        idx = int(self.slider.get())
        delay_ms = int(self.delays[idx] * 1000)

        # 오류 방지를 위해 맥 바탕화면에 시간 이름으로 자동 저장
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        save_path = os.path.join(desktop, f"my_gif_{timestamp}.gif")

        try:
            frames = []
            for path in self.image_paths:
                img = Image.open(path).convert('RGB')

                # 중앙 자르기(Center Crop) 로직
                img_w, img_h = img.size
                ratio = max(w / img_w, h / img_h)
                new_w = int(img_w * ratio)
                new_h = int(img_h * ratio)
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                left = (new_w - w) / 2
                top = (new_h - h) / 2
                right = (new_w + w) / 2
                bottom = (new_h + h) / 2
                img = img.crop((left, top, right, bottom))
                frames.append(img)

            # 256색 양자화 + Floyd-Steinberg 디더링 (색띠 제거)
            # libimagequant 가능하면 사용 (지각적 양자화, 최고 품질), 아니면 MEDIANCUT
            quantized = []
            for f in frames:
                try:
                    qf = f.quantize(colors=256, method=Image.Quantize.LIBIMAGEQUANT, dither=Image.Dither.FLOYDSTEINBERG)
                except (ValueError, OSError):
                    qf = f.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)
                quantized.append(qf)

            quantized[0].save(
                save_path,
                format='GIF',
                append_images=quantized[1:],
                save_all=True,
                duration=delay_ms,
                loop=0,
                optimize=True,
                disposal=2,
            )
            messagebox.showinfo("성공!", f"바탕화면에 저장되었습니다!\n파일명: my_gif_{timestamp}.gif")
            
        except Exception as e:
            messagebox.showerror("오류 발생", f"문제가 생겼어:\n{e}")

if __name__ == "__main__":
    # tk.Tk() 대신 TkinterDnD.Tk()를 사용해야 드래그앤드롭이 활성화됨
    root = TkinterDnD.Tk()
    app = GifMakerApp(root)
    root.mainloop()
