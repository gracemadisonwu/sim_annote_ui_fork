import os
from moviepy import VideoFileClip, AudioFileClip
from typing import List
import json
from moviepy import concatenate_audioclips, AudioFileClip, concatenate_videoclips
import torchaudio
import torch
from noisereduce.torchgate import TorchGate as TG
import tqdm
import glob

from speechbrain.inference.speaker import SpeakerRecognition

class FileProcessor:
    def __init__(self, file_path: str, whisper_results_file: str, denoise: bool = False, denoise_prop: float = 0.1,
                 verification_threshold: float = 0.2):
        if not os.path.exists(file_path):
            raise FileNotFoundError
        if not os.path.exists(whisper_results_file):
            raise FileNotFoundError
        device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
        if denoise:
            noisy_speech, self.sr = torchaudio.load(file_path)
            noisy_speech = noisy_speech.to(device)
            # Create TorchGating instance
            tg = TG(sr=self.sr, nonstationary=True, prop_decrease=denoise_prop).to(device)
            # Apply Spectral Gate to noisy speech signal
            enhanced_speech = tg(noisy_speech)
            # dn_file_path_wav = os.path.splitext(file_path)[0] + "_denoised.wav"
            # torchaudio.save(dn_file_path_wav, src=enhanced_speech.cpu(), sample_rate=sr)
            self.audio = enhanced_speech.cpu()
        else:
            self.audio, self.sr = torchaudio.load(file_path)
        self.whisper_results_file = whisper_results_file
        self.whisper_results = json.load(open(whisper_results_file))

        self.verification = SpeakerRecognition.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb", savedir=f"~/pretrained_models/spkrec-ecapa-voxceleb", run_opts={"device":"cuda"})
        self.verification_threshold = verification_threshold
        self.speaker_info = {}

    def concat_all_speaker_segments(self):
        all_speakers = set()
        for segment in self.whisper_results["segments"]:
            if "speaker" in segment:
                all_speakers.add(segment["speaker"])
        for speaker in all_speakers:
            speaker_segments = [segment for segment in self.whisper_results["segments"] if segment["speaker"] == speaker]
            speaker_segments = sorted(speaker_segments, key=lambda x: x["start"])
            speaker_segments = [self.audio[int(segment["start"] * self.sr): int(segment["end"] * self.sr)] for segment in speaker_segments]
            speaker_segments = torch.cat(speaker_segments)
            self.speaker_info[speaker] = {"reference_segments":speaker_segments}
 
    def process(self):
        self.whisper_results = json.load(open(self.whisper_results_file))
        self.concat_all_speaker_segments()
        # Iterate through each speaker and each segment
        for seg in tqdm.tqdm(self.whisper_results["segments"]):
            if "speaker" in seg and seg["speaker"] != "":
                continue
            best_speaker, best_score = None, float("-inf")
            curr_audio = self.audio[int(seg["start"] * self.sr): int(seg["end"] * self.sr)]
            try:
                for speaker in self.speaker_info:
                    # Verify the segment and try to find the best one
                    score, _ = self.verification.verify_batch(curr_audio, self.speaker_info[speaker]["reference_segments"])
                    if score > best_score:
                        best_score = score
                        best_speaker = speaker
                if best_score > self.verification_threshold:
                    seg["speaker"] = best_speaker
                    self.whisper_results["segments"][seg["id"]]["speaker"] = best_speaker
            except RuntimeError:
                continue
        json.dump(self.whisper_results, open(self.whisper_results_file, "w+"))
        
        print("Finished Processing File!! <3")