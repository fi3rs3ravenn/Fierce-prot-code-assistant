import asyncio
import subprocess
from pathlib import Path
import structlog

logger = structlog.get_logger()

async def play_video(video_path: str) -> None:
    path = Path(video_path)
    if not path.exists():
        logger.error(f"No video: {video_path}")
        return
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffplay", "-autoexit", "-nodisp", str(path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await proc.wait()
        logger.info(f"Video done: {video_path}")
    except Exception as e:
        logger.error(f"Playback crashed: {e}")