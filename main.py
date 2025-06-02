import asyncio
import threading
from services.main_gui import VideoGUI
from services.audio_plr import AudioPlayer
from services.spch_rcgnz import VoiceService, VoiceConfig
from core.txt_rtr import TextRouter

GREETING_WORDS = ["привет", "здравствуй", "добрый"]
FAREWELL_WORDS = ["спасибо", "пока", "до свидания", "благодарю"]

video_gui = VideoGUI(width=1080, height=1920)
audio_player = AudioPlayer()

def start_async_tasks():
    asyncio.run(main_logic())

def start_gui():
    threading.Thread(target=start_async_tasks, daemon=True).start()
    video_gui.mainloop()

async def main_logic():
    voice_config = VoiceConfig.from_yaml("config.yaml")
    router = TextRouter({
        "question_map": {
            "map_path": "questions_video_map.json",
            "map_path_expanded": "questions_video_map_expanded.json"
        },
        "video_dir": "videos/old",
        "fallback_video": "videos/error.mp4"
    })

    last_interaction = asyncio.get_event_loop().time()
    last_phrase = None
    is_busy = False

    video_gui.play_video("videos/main.mp4", loop=True)

    async def on_text(text: str):
        nonlocal last_interaction, last_phrase, is_busy

        if is_busy:
            return

        lowered = text.lower().strip()
        if lowered == last_phrase:
            return
        last_phrase = lowered
        last_interaction = asyncio.get_event_loop().time()
        print(f"[🗣️] TEXT: {lowered}")

        is_busy = True

        if any(word in lowered for word in GREETING_WORDS):
            video_gui.play_video("videos/welcome.mp4")
            await audio_player.play_audio("videos/welcome.mp4")
            video_gui.play_video("videos/main.mp4", loop=True)
            is_busy = False
            return

        if any(word in lowered for word in FAREWELL_WORDS):
            video_gui.play_video("videos/question.mp4")
            await audio_player.play_audio("videos/question.mp4")
            video_gui.play_video("videos/main.mp4", loop=True)
            is_busy = False
            return

        _, matched_video = await router.route(lowered)

        if matched_video == "error.mp4":
            video_gui.play_video("videos/error.mp4")
            await audio_player.play_audio("videos/error.mp4")
        else:
            video_gui.play_video(f"videos/old/{matched_video}")
            await audio_player.play_audio(f"videos/old/{matched_video}")

        if any(word in lowered for word in FAREWELL_WORDS):
            video_gui.play_video("videos/question.mp4")
            await audio_player.play_audio("videos/question.mp4")
            video_gui.play_video("videos/main.mp4", loop=True)
            is_busy = False
            return

        video_gui.play_video("videos/main.mp4", loop=True)
        is_busy = False

    service = VoiceService(voice_config, on_text)

    async def silence_check():
        while True:
            await asyncio.sleep(5)
            if asyncio.get_event_loop().time() - last_interaction > 30:
                video_gui.play_video("videos/question.mp4")
                await audio_player.play_audio("videos/question.mp4")
                service.stop_event.set()
                break

    await asyncio.gather(service.run(), silence_check())

if __name__ == "__main__":
    start_gui()