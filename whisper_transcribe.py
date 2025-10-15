import whisper
import torchaudio 
import os
from moviepy import VideoFileClip
import tqdm
import json
import torch
from logging import getLogger
import logging

logger = getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def transcribe_with_whisper(file_path: str, segment_dir: str, save_json: bool = True):
    if not file_path.endswith(".wav"):
        file_path_wav = os.path.splitext(file_path)[0] + ".wav"
        if not os.path.exists(file_path_wav):
            clip = VideoFileClip(file_path)
            if file_path.lower().endswith(".mov"):
                clip.audio.write_audiofile(file_path_wav, codec='pcm_s16le')
            else:
                clip.audio.write_audiofile(file_path_wav)
        file_path = file_path_wav
    else:
        file_path = file_path
    logger.info("Current file path " + file_path)
    
    if not torch.cuda.is_available():
        device = "cpu"
        model = whisper.load_model("small", device=device)
    else:
        device = "cuda"
        model = whisper.load_model("large", device=device)
    
    try:
        # if os.path.exists(f"{segment_dir}/whisper_results.json"):
        #     result = json.load(open(f"{segment_dir}/whisper_results.json"))
        # elif os.path.exists(os.path.join(os.path.dirname(file_path), "whisper_results.json")):
        #     result = json.load(open(os.path.join(os.path.dirname(file_path), "whisper_results.json")))
        # else:
        result = model.transcribe(file_path, word_timestamps=True)
        if save_json:
            json.dump(result, open(f"{segment_dir}/whisper_results.json", "w"))
    except Exception as e:
        logger.info(str(e))
    return result, file_path
