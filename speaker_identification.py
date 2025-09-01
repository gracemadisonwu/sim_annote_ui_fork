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

    def concat_all_speaker_segments(self):
        all_speakers = set()
        for segment in self.whisper_results["segments"]:
            if segment.get("speaker"):  # Only process segments that already have speakers
                all_speakers.add(segment["speaker"])
        
        for speaker in all_speakers:
            speaker_segments = [segment for segment in self.whisper_results["segments"] if segment.get("speaker") == speaker]
            speaker_segments = sorted(speaker_segments, key=lambda x: x["start"])
            
            # Extract audio segments with validation
            valid_audio_segments = []
            for segment in speaker_segments:
                start_sample = int(segment["start"] * self.sr)
                end_sample = int(segment["end"] * self.sr)
                
                # Validate segment bounds
                if start_sample >= end_sample or start_sample < 0 or end_sample > self.audio.shape[-1]:
                    continue
                
                audio_segment = self.audio[:, start_sample:end_sample]
                
                # Check if segment has sufficient length (at least 0.1 seconds)
                if audio_segment.shape[-1] < int(0.1 * self.sr):
                    continue
                
                valid_audio_segments.append(audio_segment)
            
            if valid_audio_segments:
                try:
                    speaker_segments_concat = torch.cat(valid_audio_segments, dim=-1)
                    # Ensure proper format for SpeechBrain
                    speaker_segments_concat = self._ensure_audio_format(speaker_segments_concat)
                    self.speaker_info[speaker] = {"reference_segments": speaker_segments_concat}
                except Exception as e:
                    print(f"Error concatenating segments for speaker {speaker}: {e}")
                    continue
 
    def process(self):
        self.whisper_results = json.load(open(self.whisper_results_file))
        self.concat_all_speaker_segments()
        
        # Check if we have any reference speakers
        if not self.speaker_info:
            print("No reference speakers found. Please manually label some segments first.")
            return
        
        # Iterate through each segment
        for seg in tqdm.tqdm(self.whisper_results["segments"]):
            if seg.get("speaker", "") != "":
                continue
                
            # Validate segment bounds
            start_sample = int(seg["start"] * self.sr)
            end_sample = int(seg["end"] * self.sr)
            
            if start_sample >= end_sample or start_sample < 0 or end_sample > self.audio.shape[-1]:
                continue
                
            # Extract current audio segment
            curr_audio = self.audio[:, start_sample:end_sample]
            
            # Check if segment has sufficient length (at least 0.1 seconds)
            if curr_audio.shape[-1] < int(0.1 * self.sr):
                continue
            
            best_speaker, best_score = None, float("-inf")
            
            # try:
            # Ensure current audio is properly formatted
            curr_audio = self._ensure_audio_format(curr_audio)
            print(best_speaker, best_score, self.verification_threshold, seg)
            
            for speaker in self.speaker_info:
                # Verify the segment and try to find the best one
                score, _ = self.verification.verify_batch(curr_audio, self.speaker_info[speaker]["reference_segments"])
                print(score)
                if score > best_score:
                    best_score = score
                    best_speaker = speaker
                    
            if best_score > self.verification_threshold:
                seg["speaker"] = best_speaker
                # Also update the segment by ID if it exists
                for segment in self.whisper_results["segments"]:
                    if segment.get("id") == seg.get("id"):
                        segment["speaker"] = best_speaker
                        break
                            
            # except RuntimeError as e:
            #     print(f"Runtime error processing segment {seg.get('id', 'unknown')}: {e}")
            #     print(best_speaker, best_score, self.verification_threshold, seg)
            #     continue
            # except Exception as e:
            #     print(f"Unexpected error processing segment {seg.get('id', 'unknown')}: {e}")
            #     continue
                
        json.dump(self.whisper_results, open(self.whisper_results_file, "w+"))
        
        print("Finished Processing File!! <3")