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
import copy
from whisper_transcribe import transcribe_with_whisper
from thefuzz import fuzz

from speechbrain.inference.speaker import SpeakerRecognition

class MultiChannelFileProcessor:
    def __init__(self, file_path: str, whisper_results_file: str, denoise: bool = False, denoise_prop: float = 0.1,
                 verification_threshold: float = 0.2):
        if not os.path.exists(file_path):
            raise FileNotFoundError
        if not os.path.exists(whisper_results_file):
            raise FileNotFoundError
        # device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
        # if denoise:
        #     noisy_speech, self.sr = torchaudio.load(file_path)
        #     noisy_speech = noisy_speech.to(device)
        #     # Create TorchGating instance
        #     tg = TG(sr=self.sr, nonstationary=True, prop_decrease=denoise_prop).to(device)
        #     # Apply Spectral Gate to noisy speech signal
        #     enhanced_speech = tg(noisy_speech)
        #     # dn_file_path_wav = os.path.splitext(file_path)[0] + "_denoised.wav"
        #     # torchaudio.save(dn_file_path_wav, src=enhanced_speech.cpu(), sample_rate=sr)
        #     self.audio = enhanced_speech.cpu()
        # else:
        self.audio, self.sr = torchaudio.load(file_path)
        self.extract_channels_from_audio(file_path)
        self.whisper_results_file = whisper_results_file
        self.whisper_results = json.load(open(whisper_results_file))
        if "segments" not in self.whisper_results:
            new_results = {"segments": copy.deepcopy(self.whisper_results)}
            self.whisper_results = new_results
        self.speaker_results = copy.deepcopy(self.whisper_results)
        self.extract_speaker_from_whisper()
        self.channel_transcripts = {}
        self.channel_speaker_mapping = {}

        # Try CUDA first, fallback to CPU if there are issues
        try:
            if torch.cuda.is_available():
                self.verification = SpeakerRecognition.from_hparams(
                    source="speechbrain/spkrec-ecapa-voxceleb", 
                    savedir=f"~/pretrained_models/spkrec-ecapa-voxceleb", 
                    run_opts={"device":"cuda"}
                )
                print("Using CUDA for speaker recognition")
            else:
                raise RuntimeError("CUDA not available")
        except Exception as e:
            print(f"CUDA initialization failed: {e}. Falling back to CPU.")
            self.verification = SpeakerRecognition.from_hparams(
                source="speechbrain/spkrec-ecapa-voxceleb", 
                savedir=f"~/pretrained_models/spkrec-ecapa-voxceleb", 
                run_opts={"device":"cpu"}
            )
            
        self.verification_threshold = verification_threshold
        self.speaker_info = {}
        
    def _ensure_audio_format(self, audio_tensor):
        """Ensure audio tensor is properly formatted for processing"""
        # Ensure tensor is 2D (channels, samples)
        if audio_tensor.dim() == 1:
            audio_tensor = audio_tensor.unsqueeze(0)
        elif audio_tensor.dim() > 2:
            audio_tensor = audio_tensor.squeeze()
            
        # Ensure tensor is on CPU (SpeechBrain expects CPU tensors)
        if audio_tensor.device.type != 'cpu':
            audio_tensor = audio_tensor.cpu()
            
        return audio_tensor
    
    def extract_channels_from_audio(self, file_path: str):
        for channel in range(len(self.audio)):
            if not os.path.exists(f"{file_path.replace('.wav', f'_channel_{channel}.wav')}"):
                curr_audio = self.audio[channel, :]
                curr_audio = self._ensure_audio_format(curr_audio)
                device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
                curr_audio = curr_audio.to(device)
                # Create TorchGating instance
                tg = TG(sr=self.sr, nonstationary=True, prop_decrease=0.4).to(device)
                # Apply Spectral Gate to noisy speech signal
                enhanced_speech = tg(curr_audio)
                torchaudio.save(f"{file_path.replace('.wav', f'_channel_{channel}.wav')}", src=enhanced_speech.cpu(), sample_rate=self.sr)
                torch.cuda.empty_cache()
            self.channel_transcripts[channel], _ = transcribe_with_whisper(f"{file_path.replace('.wav', f'_channel_{channel}.wav')}", "data/segments-channel_{channel}", save_json=False)

    def extract_speaker_from_whisper(self):
        for s in self.whisper_results["segments"]:
            if len(s["speaker"]):
                if s["speaker"] not in self.speaker_info:
                    self.speaker_info[s["speaker"]] = {"reference_segments": [s["text"]]}
                else:
                    self.speaker_info[s["speaker"]]["reference_segments"].append(s["text"])
    
    def extract_speaker_from_channel_transcripts(self):
        speaker_channel_mapping = {}
        for speaker in self.speaker_info:
            speaker_channel_mapping[speaker] = []
            for channel in self.channel_transcripts:
                for ref_seg in self.speaker_info[speaker]["reference_segments"]:
                    if fuzz.partial_ratio(ref_seg, self.channel_transcripts[channel]["text"]) > 80:
                        speaker_channel_mapping[speaker].append(channel)
        channel_speaker_mapping = {}
        for speaker in speaker_channel_mapping:
            if len(speaker_channel_mapping[speaker]) == 1:
                channel_speaker_mapping[speaker_channel_mapping[speaker][0]] = speaker
            else:
                all_channel_texts = [(channel, len(self.channel_transcripts[channel]["text"])) for channel in speaker_channel_mapping[speaker]]
                all_channel_texts = sorted(all_channel_texts, key=lambda x: x[1])
                channel_speaker_mapping[all_channel_texts[0][0]] = speaker
            # If more than one channel is associated with the same speaker, we need to determine the best channel
        if len(channel_speaker_mapping) != len(self.speaker_info):
            print("Some speakers are not mapped to any channel")
            return None
        for channel in channel_speaker_mapping:
            self.speaker_info[channel_speaker_mapping[channel]]["channel"] = channel
        for channel in self.channel_transcripts:
            self.channel_transcripts[channel]["speaker"] = channel_speaker_mapping[channel]
        return channel_speaker_mapping
    
    def anchor_audio_and_video(self):
        # Find longest utterance
        all_segs = copy.deepcopy(self.whisper_results["segments"])
        all_segs = sorted(all_segs, key=lambda x: x["end"] - x["start"], reverse=True)
        longest_seg = all_segs[0]

        end_time = self.whisper_results["segments"][-1]["end"]
        # Assuming that the video is shorter than the audio
        for channel in self.channel_transcripts:
            for seg in self.channel_transcripts[channel]["segments"]:
                if seg["text"] == longest_seg["text"]:
                    selected_seg = seg
                    break
        diff = selected_seg["end"] - selected_seg["start"]
        for channel in self.channel_transcripts:
            for i in range(len(self.channel_transcripts[channel]["segments"])):
                self.channel_transcripts[channel]["segments"][i]["start"] -= diff
                self.channel_transcripts[channel]["segments"][i]["end"] -= diff
        for channel in self.channel_transcripts:
            self.channel_transcripts[channel]["segments"] = [x for x in self.channel_transcripts[channel]["segments"] if x["end"] < end_time]
     
    
    def process(self):
        self.extract_speaker_from_channel_transcripts()
        self.anchor_audio_and_video()

        final_speaker_results = {"segments": []}
        
        for channel in self.channel_transcripts:
            if channel in self.channel_speaker_mapping:
                for seg in self.channel_transcripts[channel]["segments"]:
                    seg["speaker"] = self.channel_speaker_mapping[channel]
                    final_speaker_results["segments"].append(seg)
        final_speaker_results["segments"] = sorted(final_speaker_results["segments"], key=lambda x: x["start"])
        json.dump(final_speaker_results, open(self.whisper_results_file.replace(".json", "_speaker_results.json"), "w+"))

    



    
