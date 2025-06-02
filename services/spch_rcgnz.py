import asyncio
import queue
import sys
import json
import sounddevice as sd
import vosk
import numpy as np
import yaml
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable, Optional
from pathlib import Path
import structlog
import logging
from collections import deque

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True
)
logger = structlog.get_logger()
logging.getLogger().setLevel(logging.INFO)

@dataclass
class VoiceConfig:
    model_path: str = "vosk-model-small-ru-0.22"
    samplerate: int = 16000
    blocksize: int = 8000
    device: Optional[int] = None
    max_workers: int = 2
    min_text_length: int = 3
    min_confidence: float = 0.7
    max_partial_wait: float = 1.0
    repeat_window: float = 2.0 

    @classmethod
    def from_yaml(cls, path: str) -> 'VoiceConfig':
        try:
            with open(path, 'r') as f:
                data = yaml.safe_load(f) or {}
                valid_keys = cls.__annotations__.keys()
                filtered_data = {k: v for k, v in data.items() if k in valid_keys}
                return cls(**filtered_data)
        except Exception as e:
            logger.error("Config load failed", error=str(e))
            return cls()

class VoiceService:
    def __init__(self, config: VoiceConfig, on_text: Callable[[str], None]):
        self.config = config
        self.on_text = on_text
        self.queue = queue.Queue()
        self.model = self._load_model()
        self.rec = vosk.KaldiRecognizer(self.model, self.config.samplerate)
        self.stop_event = asyncio.Event()
        self.partial_text = ""
        self.last_update = asyncio.get_event_loop().time()
        self.recent_phrases = deque(maxlen=5) 

    def _load_model(self) -> vosk.Model:
        if not Path(self.config.model_path).exists():
            logger.error(f"No model: {self.config.model_path}")
            sys.exit(1)
        return vosk.Model(self.config.model_path)

    def audio_callback(self, indata: np.ndarray, frames: int, time, status):
        if status:
            logger.error(f"Audio glitch: {status}")
        if not isinstance(indata, np.ndarray):
            indata = np.frombuffer(indata, dtype=np.int16)
        self.queue.put(indata.tobytes())

    async def _process_text(self, text: str):
        current_time = asyncio.get_event_loop().time()
        for phrase, timestamp in self.recent_phrases:
            if text == phrase and (current_time - timestamp) < self.config.repeat_window:
                logger.debug(f"Skipping repeat: {text}")
                return
        try:
            maybe_coro = self.on_text(text)
            if asyncio.iscoroutine(maybe_coro):
                await maybe_coro
            self.recent_phrases.append((text, current_time))
        except Exception as e:
            logger.error(f"Callback crashed: {e}")

    async def _process_audio(self, data: bytes):
        current_time = asyncio.get_event_loop().time()
        if self.rec.AcceptWaveform(data):
            result = json.loads(self.rec.Result())
            self.rec.Reset()
            text = result.get("text", "").strip()
            confidence = result.get("result", [{}])[0].get("confidence", 1.0) if result.get("result") else 1.0
            if text and len(text) > self.config.min_text_length and confidence >= self.config.min_confidence:
                if self.partial_text and self.partial_text not in text:
                    text = self.partial_text + " " + text
                    self.partial_text = ""
                await self._process_text(text)
            self.last_update = current_time
        else:
            result = json.loads(self.rec.PartialResult())
            partial = result.get("partial", "").strip()
            if partial and len(partial) > self.config.min_text_length:
                if partial != self.partial_text: 
                    self.partial_text = partial
                    self.last_update = current_time
            elif self.partial_text and (current_time - self.last_update > self.config.max_partial_wait):
                await self._process_text(self.partial_text)
                self.partial_text = ""
                self.last_update = current_time

    async def recognize_loop(self):
        while not self.stop_event.is_set():
            try:
                data = self.queue.get_nowait()
                await self._process_audio(data)
            except queue.Empty:
                await asyncio.sleep(0.01)
            except Exception as e:
                logger.error(f"Recognition crash: {e}")


    async def start_audio(self):
        try:
            self.stream = sd.RawInputStream(
                samplerate=self.config.samplerate,
                blocksize=self.config.blocksize,
                device=self.config.device,
                dtype='int16',
                channels=1,
                callback=self.audio_callback
            )
            self.stream.start()
            logger.info("Mic hot")
        except Exception as e:
            logger.error(f"Audio start failed: {e}")
            sys.exit(1)

    async def run(self):
        await self.start_audio()
        try:
            await self.recognize_loop()
        except asyncio.CancelledError:
            logger.info("Voice down")
            self.stream.stop()
            self.stream.close()

    def __del__(self):
        if hasattr(self, 'stream') and self.stream.is_active():
            self.stream.stop()
            self.stream.close()