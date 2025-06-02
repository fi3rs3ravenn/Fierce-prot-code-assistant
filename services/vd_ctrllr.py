# services/vd_ctrllr.py

import asyncio
import subprocess
from pathlib import Path

class VideoController:
    def __init__(self):
        self.process = None
        self.ffplay_path = r"C:\ffmpeg\bin\ffplay.exe"  # УКАЖИ свой путь

    async def play(self, video_path: str, loop: bool = False):
        await self.stop()
        path = Path(video_path)
        if not path.exists():
            print(f"[!] Video not found: {video_path}")
            return

        args = [
         self.ffplay_path,
            "-autoexit",
            "-loglevel", "quiet",
            str(path)
        ]
        if loop:
            args = [
                self.ffplay_path,
                "-loop", "0",
                "-loglevel", "quiet",
                str(path)
            ]

        self.process = await asyncio.create_subprocess_exec(*args)
        if not loop:
            await self.process.wait()  # ⬅️ Ждём окончания


    async def stop(self):
        if self.process and self.process.returncode is None:
            self.process.terminate()
            try:
                await self.process.wait()
            except:
                pass
            self.process = None
