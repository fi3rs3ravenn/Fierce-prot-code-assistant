import asyncio
from pathlib import Path

class AudioPlayer:
    def __init__(self):
        self.process = None
        self.ffplay = r"C:\ffmpeg\bin\ffplay.exe"  # Укажи путь

    async def play_audio(self, path):
        if not Path(path).exists():
            print(f"[AUDIO] File not found: {path}")
            return
        self.process = await asyncio.create_subprocess_exec(
            self.ffplay,
            "-nodisp", "-autoexit", "-loglevel", "quiet",
            path
        )
        await self.process.wait()
