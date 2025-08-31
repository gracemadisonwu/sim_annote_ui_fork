import whisper
import torchaudio 
import os
from moviepy import VideoFileClip
import tqdm
import json
import torch

def transcribe_with_whisper(file_path: str, segment_dir: str):
    if not file_path.endswith(".wav"):
        file_path_wav = os.path.splitext(file_path)[0] + ".wav"
        if not os.path.exists(file_path_wav):
            clip = VideoFileClip(file_path)
            clip.audio.write_audiofile(file_path_wav)
        file_path = file_path_wav
    else:
        file_path = file_path
    
    if not torch.cuda.is_available():
        device = "cpu"
        model = whisper.load_model("small", device=device)
    else:
        device = "cuda"
        model = whisper.load_model("turbo", device=device)
    
    if os.path.exists(f"{segment_dir}/whisper_results.json"):
        result = json.load(open(f"{segment_dir}/whisper_results.json"))
    elif os.path.exists(os.path.join(os.path.dirname(file_path), "whisper_results.json")):
        result = json.load(open(os.path.join(os.path.dirname(file_path), "whisper_results.json")))
    else:
        result = model.transcribe(file_path, word_timestamps=True)
    json.dump(result, open(f"{segment_dir}/whisper_results.json", "w"))
    return result, file_path
