import json
from pathlib import Path
from typing import Optional, Dict
from sentence_transformers import SentenceTransformer, util
import torch
import structlog

logger = structlog.get_logger()
class QuestionMatcher:
    def __init__(self, config: dict):
        self.map_path_main = Path(config.get("map_path", "questions_video_map.json"))
        self.map_path_fallback = Path(config.get("map_path_expanded", "questions_video_map_expanded.json"))
        self.match_threshold = config.get("match_threshold", 0.6)

        self.model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

        self.video_map_main = self._load_map(self.map_path_main)
        self.questions_main, self.video_links_main = self._prepare(self.video_map_main)
        self.embeddings_main = self.model.encode(self.questions_main, convert_to_tensor=True)

        self.video_map_fallback = self._load_map(self.map_path_fallback)
        self.questions_fallback, self.video_links_fallback = self._prepare(self.video_map_fallback)
        self.embeddings_fallback = self.model.encode(self.questions_fallback, convert_to_tensor=True)

        logger.info("SBERT ready")

    def _load_map(self, path: Path) -> Dict[str, list]:
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"map crash: {e}")
            raise

    def _prepare(self, video_map: dict):
        questions = []
        video_links = []
        for video, qlist in video_map.items():
            for q in qlist:
                questions.append(q)
                video_links.append(video)
        return questions, video_links

    async def match(self, user_text: str) -> Optional[tuple]:
        user_text = user_text.lower().strip()
        if not user_text:
            return None, None

        emb = self.model.encode(user_text, convert_to_tensor=True)

        sims_main = util.cos_sim(emb, self.embeddings_main)[0]
        best_score_main = float(torch.max(sims_main))
        best_index_main = int(torch.argmax(sims_main))

        if best_score_main >= self.match_threshold:
            video = self.video_links_main[best_index_main]
            question = self.questions_main[best_index_main]
            logger.info("matched main", score=best_score_main, question=question)
            return question, video

        sims_fb = util.cos_sim(emb, self.embeddings_fallback)[0]
        best_score_fb = float(torch.max(sims_fb))
        best_index_fb = int(torch.argmax(sims_fb))

        if best_score_fb >= self.match_threshold:
            video = self.video_links_fallback[best_index_fb]
            question = self.questions_fallback[best_index_fb]
            logger.info("FALLBACK", score=best_score_fb, question=question)
            return question, video

        logger.warning("no match")
        return None, None
