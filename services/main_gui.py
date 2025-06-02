import tkinter as tk
import cv2
from PIL import Image, ImageTk

class VideoGUI:
    def __init__(self, width=540, height=960):
        self.root = tk.Tk()
        self.root.title("AI Assistant")
        self.root.geometry(f"{width}x{height}")
        self.root.resizable(False, False)
        self.label = tk.Label(self.root)
        self.label.pack()
        self.width = width
        self.height = height
        self.video_path = None
        self.running = False
        self.loop = False
        self.cap = None

    def mainloop(self):
        self._update_frame()
        self.root.mainloop()

    def play_video(self, path, loop=False):
        if self.cap:
            self.cap.release()
        self.cap = cv2.VideoCapture(path)
        self.running = True
        self.loop = loop

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()

    def _update_frame(self):
        try:
            if self.running and self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if not ret:
                    if self.loop:
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = self.cap.read()
                    else:
                        self.running = False
                        return

                if ret:
                    frame = cv2.resize(frame, (self.width, self.height))
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    image = ImageTk.PhotoImage(image=Image.fromarray(frame))
                    self.label.configure(image=image)
                    self.label.image = image
        except Exception as e:
            print(f"[FRAME ERROR] {e}")

        fps = self.cap.get(cv2.CAP_PROP_FPS) if self.cap else 30
        delay = int(1000 / (fps or 30))
        self.root.after(delay, self._update_frame)
