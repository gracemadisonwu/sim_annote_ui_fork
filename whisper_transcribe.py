import whisper
import torchaudio
import os
from moviepy import VideoFileClip
import tqdm
import json
import torch
from logging import getLogger
import logging
import subprocess

logger = getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def transcribe_with_whisper(file_path: str, segment_dir: str, save_json: bool = True):
    if not file_path.endswith(".wav"):
        file_path_wav = os.path.splitext(file_path)[0] + ".wav"
        if not os.path.exists(file_path_wav):
            # Use FFmpeg directly for MOV files to avoid moviepy metadata parsing issues
            if file_path.lower().endswith(".mov"):
                logger.info(f"Extracting audio from MOV file using FFmpeg: {file_path}")
                try:
                    subprocess.run([
                        'ffmpeg', '-i', file_path,
                        '-vn',  # No video
                        '-acodec', 'pcm_s16le',  # 16-bit PCM WAV
                        '-ar', '16000',  # 16kHz sample rate (good for speech/Whisper)
                        '-ac', '1',  # Mono
                        file_path_wav
                    ], check=True, capture_output=True, text=True)
                    logger.info(f"Successfully extracted audio to: {file_path_wav}")
                except subprocess.CalledProcessError as e:
                    logger.error(f"FFmpeg extraction failed: {e.stderr}")
                    raise
            else:
                # Use moviepy for other video formats
                clip = VideoFileClip(file_path)
                clip.audio.write_audiofile(file_path_wav)
                clip.close()
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
