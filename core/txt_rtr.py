import asyncio
from pathlib import Path
import structlog
from core.qstn_mchr import QuestionMatcher

logger = structlog.get_logger()

class TextRouter:
    def __init__(self, config: dict):
        self.matcher = QuestionMatcher(config.get("question_map", {}))
        self.video_dir = Path(config.get("video_dir", "videos"))
        self.fallback = Path(config.get("fallback_video", "videos/error.mp4"))

    async def route(self, user_text: str):
        logger.info(f"Text in: {user_text}")
        
        try:
            question, videos = await self.matcher.match(user_text)

            if not videos:
                raise ValueError("No video match found")

            if isinstance(videos, list):
                video_file = videos[0] if videos else None
            else:
                video_file = videos

            if not video_file:
                raise ValueError("Empty video reference")

            video_path = self.video_dir / video_file
            print(f"Matched: {question}")
            print(f"VIDEO PATH: {video_path}")
            return question, video_file

        except Exception as e:
            logger.error(f"Error in route: {e}")
            print(f"Fallback used")
            print(f"VIDEO PATH: {self.fallback}")
            return None, self.fallback.name