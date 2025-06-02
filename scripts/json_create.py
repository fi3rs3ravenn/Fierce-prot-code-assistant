from collections import defaultdict
import json
import pandas as pd
xlsx_path = r"C:\Users\quindecim\Desktop\prot-code\ChatBotData.xlsx" 
df = pd.read_excel(xlsx_path, sheet_name=0)
questions = df["Вопросы"]
video_names = df["Видео с озвучкой"]

video_map = defaultdict(list)

for question, video in zip(questions, video_names):
    if pd.notna(question) and pd.notna(video) and str(video).strip().endswith(".mp4"):
        video = str(video).strip()
        question = str(question).strip()
        video_map[video].append(question)

video_map = dict(video_map)
output_path = "///questions_video_map.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(video_map, f, ensure_ascii=False, indent=2)

output_path
